import asyncio
import os
import copy
import traceback
import signal
import sys
from google import genai

# 개별 모듈 임포트
from api_loader import WeddingApiLoader
from collector import WeddingDataCollector
from processor import WeddingDataProcessor
from preprocessor import DataPreprocessor
from storage import WeddingDataStorage

from config import config

# ==========================================
# [전역 종료 플래그 및 신호 처리]
# ==========================================
shutdown_requested = False
sigint_count = 0

def signal_handler(sig, frame):
    global shutdown_requested, sigint_count
    sigint_count += 1
    
    if sigint_count >= 3:
        print("\n[!!!] 강제 종료 신호(3회) 감지. 즉시 종료합니다.")
        sys.exit(1)
    
    if not shutdown_requested:
        shutdown_requested = True
        print("\n[!] 종료 신호 감지. 현재 진행 중인 작업까지만 완료하고 안전하게 종료합니다.")
        print("    (즉시 종료하시려면 Ctrl+C를 2번 더 누르세요.)")

# 시그널 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# [설정 및 환경변수]
# ==========================================
GEMINI_API_KEY = config.google_api_key
if not GEMINI_API_KEY:
    raise ValueError("API 키를 찾을 수 없습니다. config.json 또는 .env.local 확인 필요")

client = genai.Client(api_key=GEMINI_API_KEY)


class ProgressTracker:
    """비동기 병렬 처리 중 진행 상황을 추적합니다."""
    def __init__(self, total):
        self.total = total
        self.processed = 0
        self.lock = asyncio.Lock()

    async def increment(self):
        async with self.lock:
            self.processed += 1
            percent = (self.processed / self.total) * 100
            return f"[{self.processed}/{self.total} ({percent:.1f}%)]"


async def run_single_campaign(api_basic_data: dict, collector, processor, preprocessor, storage, semaphore, tracker: ProgressTracker):
    """
    개별 캠페인에 대한 전처리 -> 수집 -> 분석 -> 저장 주기를 실행합니다.
    """
    # [중요] 이미 종료 신호가 왔다면 새 작업을 시작하지 않고 대기합니다.
    if shutdown_requested:
        return

    async with semaphore:
        # 세마포어 안으로 들어온 후에도 다시 한번 체크 (대기 중에 신호가 왔을 수 있음)
        if shutdown_requested:
            return
            
        campaign_id = api_basic_data["campaign_id"]
        target_url = api_basic_data["ad_url"]

        max_retries = config.max_retries
        for attempt in range(max_retries + 1):
            try:
                # 작업 시작 로그에 진행률 포함 (선택사항이나 여기서는 결과 로그에만 집중)
                print(f"\n[*] [{campaign_id}] 작업 시작... (시도 {attempt + 1}/{max_retries + 1})")

                # 1. 전처리 (Preprocessor)
                preprocessed = preprocessor.preprocess(api_basic_data)

                # 2. 캡처 (Collector)
                screenshot_path = storage.get_capture_path(campaign_id)
                await collector.capture_full_page_mobile(target_url, screenshot_path)

                # 3. AI 분석 (Processor)
                raw_ai_data = processor.analyze_image(screenshot_path, api_basic_data, preprocessed)

                # 4. 병합 (Processor)
                final_data = processor.smart_merge(raw_ai_data, api_basic_data, campaign_id, preprocessed)

                # 5. 저장 (Storage)
                storage.save_final_results(final_data)

                # 6. 캐시 업데이트
                clean_data = {k: v for k, v in api_basic_data.items() if k != "campaign_id"}
                storage.update_api_cache(campaign_id, clean_data)

                progress_log = await tracker.increment()
                print(f"{progress_log} [✔] [{campaign_id}] 처리 성공!")
                break

            except Exception as e:
                if attempt < max_retries:
                    print(f"[!] [{campaign_id}] 시도 {attempt + 1} 실패: {e}")
                    wait_time = (attempt + 1) * config.get("pipeline", "retry_delay_seconds", 3)
                    print(f"[-] {wait_time}초 후 다시 시도합니다...")
                    await asyncio.sleep(wait_time)
                else:
                    progress_log = await tracker.increment()
                    print(f"{progress_log} [✘] [{campaign_id}] 모든 재시도 실패. (건너뜀)")


async def main_optimized():
    """메인 실행 엔진: API 로딩, 캐시 비교, 병렬 실행 제어"""
    print("=" * 40)
    print(f"[*] 웨딩 CPA 데이터 파이프라인 시작 (Model: {config.ai_model})")
    print("=" * 40)

    # 데이터 디렉토리 설정 (환경 변수 우선)
    base_data_dir = os.getenv("DATA_DIR", "data/weddinggo")
    capture_dir = os.getenv("CAPTURE_DIR", "data/captures")
    cache_path = os.path.join(base_data_dir, "api_cache.json")

    try:
        # 객체 초기화
        collector = WeddingDataCollector()
        processor = WeddingDataProcessor(client)
        preprocessor = DataPreprocessor()
        storage = WeddingDataStorage(base_dir=base_data_dir, capture_dir=capture_dir)

        # 1. API 데이터 로딩
        full_response = await WeddingApiLoader.fetch_all_ads()
        storage.save_raw_api_data(full_response)  # 원본 전체 데이터 백업
        
        new_ads_dict = full_response.get("advertisements", {})
        cached_ads_dict = storage.read_json(cache_path)

        # 1-2. 종료된 캠페인 정리 (Cleanup defunct campaigns)
        removed_count = 0
        for cached_cid in list(cached_ads_dict.keys()):
            if cached_cid not in new_ads_dict:
                print(f"[*] [{cached_cid}] 종료된 캠페인 감지. 관련 데이터를 삭제합니다.")
                storage.delete_campaign_data(cached_cid)
                removed_count += 1
        
        if removed_count > 0:
            print(f"[*] 총 {removed_count}건의 종료된 캠페인을 정리했습니다.")

        # 2. 변경대상 선별 (Incremental Update)
        target_ads = []
        skip_count = 0

        for cid, new_data in new_ads_dict.items():
            is_file_exists = storage.is_campaign_exists(cid)
            cached_data = cached_ads_dict.get(cid)

            if cached_data and "campaign_id" in cached_data:
                cached_data = {k: v for k, v in cached_data.items() if k != "campaign_id"}
                cached_ads_dict[cid] = cached_data

            if not is_file_exists:
                ad_copy = copy.deepcopy(new_data)
                ad_copy["campaign_id"] = cid
                target_ads.append(ad_copy)
            else:
                if cached_data is None:
                    storage.update_api_cache(cid, new_data)
                    skip_count += 1
                else:
                    if new_data != cached_data:
                        ad_copy = copy.deepcopy(new_data)
                        ad_copy["campaign_id"] = cid
                        target_ads.append(ad_copy)
                    else:
                        skip_count += 1

        if skip_count > 0:
            print(f"[*] 기존 수집 데이터 {skip_count}건을 스킵합니다. (중복 방지)")

        if not target_ads:
            print("[*] 변경된 캠페인이 없습니다. 종료합니다.")
            return

        print(f"[*] 총 {len(target_ads)}건의 변경/신규 캠페인 수합 시작...")

        # 3. 비동기 병렬 실행 제어 (config.max_workers 스레드)
        semaphore = asyncio.Semaphore(config.max_workers)
        tracker = ProgressTracker(total=len(target_ads))
        await collector.start()

        tasks = [
            run_single_campaign(ad_data, collector, processor, preprocessor, storage, semaphore, tracker)
            for ad_data in target_ads
        ]
        await asyncio.gather(*tasks)

        # 4. 마무리
        storage.write_json(cache_path, new_ads_dict)
        print("\n[*] API 캐시 업데이트 및 작업 완료.")

    except Exception as e:
        print(f"[✘] 메인 로직 오류: {e}")
        traceback.print_exc()
    finally:
        if "collector" in locals():
            await collector.stop()


if __name__ == "__main__":
    asyncio.run(main_optimized())
