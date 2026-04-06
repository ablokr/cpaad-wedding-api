import asyncio
import json
import os
import time
from datetime import date
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError


# ==========================================
# [설정 및 환경변수 영역]
# ==========================================
load_dotenv()
load_dotenv(".env.local")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("API 키를 찾을 수 없습니다. .env 또는 .env.local 확인 필요")

client = genai.Client(api_key=GEMINI_API_KEY)


# ==========================================
# [영역 0: API 데이터 로더 (Loader)]
# 외부 API 서버에서 광고 데이터를 실시간으로 가져옴
# ==========================================
class WeddingApiLoader:
    API_URL = "https://cpaad.co.kr/api/ad_json.php"

    @classmethod
    async def fetch_all_ads(cls):
        print(f"[*] API 데이터 로딩 중: {cls.API_URL}")
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(cls.API_URL)
            response.raise_for_status()
            data = response.json()
            return data.get("advertisements", {})


# ==========================================
# [영역 1: 수집 (Collector)]
# ==========================================
class WeddingDataCollector:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def capture_full_page_mobile(self, url: str, output_path: str):
        print(f"[*] 웹페이지 모바일 캡처 시작: {url}")
        if not self.browser:
            await self.start()

        device_config = self.playwright.devices['iPhone 13']
        custom_config = dict(device_config)
        custom_config["device_scale_factor"] = 1 
        
        context = await self.browser.new_context(**custom_config) 
        page = await context.new_page()
        
        try:
            print(f"[-] [{url}] 페이지 로딩 중...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 무한 스크롤 대비 점진적 스크롤
            current_pos = 0
            step = 1000 
            while True:
                total_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate(f"window.scrollTo(0, {current_pos + step})")
                current_pos += step
                await page.wait_for_timeout(500) 
                if current_pos >= total_height: break
            
            await page.wait_for_timeout(2000) 
            
            print(f"[-] [{url}] 이미지 저장 중...")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            await page.screenshot(path=output_path, full_page=True, animations="disabled", timeout=120000)
            print(f"[+] 캡처 완료: {output_path}")
        finally:
            await page.close()
            await context.close()


# ==========================================
# [영역 2: 처리 (Processor)]
# ==========================================
class SeoMetadata(BaseModel):
    title: str = Field(..., description="SEO 제목")
    meta_description: str = Field(..., description="SEO 설명")
    keywords: List[str] = Field(default_factory=list)

class MarketingHooks(BaseModel):
    primary_headline: str = Field(..., description="주 헤드라인")
    secondary_headline: str = Field(..., description="보조 헤드라인")
    urgency_text: str = Field("", description="긴박감 유도 문구")
    call_to_action_text: str = Field(..., description="CTA 버튼 문구")

class Benefits(BaseModel):
    visit_gifts: List[str] = Field(default_factory=list)
    contract_benefits: List[str] = Field(default_factory=list)
    special_events: List[str] = Field(default_factory=list)

class EventInfo(BaseModel):
    start_date: Optional[date] = Field(None, description="시작 날짜 (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="종료 날짜 (YYYY-MM-DD)")
    display_date: str = Field(..., description="화면에 표시될 날짜 텍스트")

class LocationInfo(BaseModel):
    sido: str = Field(..., description="시도 (예: 서울, 경기)")
    sido_en: Optional[str] = None
    sigungu: str = Field(..., description="시군구")
    sigungu_en: Optional[str] = None
    address: str = Field("", description="상세 주소")
    venue: str = Field(..., description="개최 장소명")
    parking_info: str = Field("", description="주차 정보")

class EventDetails(BaseModel):
    event: EventInfo
    location: LocationInfo

class ConversionAndTrust(BaseModel):
    required_form_fields: List[str] = Field(default_factory=list)
    gift_conditions: str = Field("", description="경품 수령 조건")
    trust_indicators: List[str] = Field(default_factory=list)

class WeddingCpaData(BaseModel):
    campaign_id: Optional[str] = None
    gather_name: str = Field(..., description="수집 대상 명칭")
    seo_metadata: SeoMetadata
    detail_page_intro: str = Field(..., description="상세 페이지 인트로")
    marketing_hooks: MarketingHooks
    benefits: Benefits
    event_details: EventDetails
    conversion_and_trust: ConversionAndTrust


class WeddingDataProcessor:
    def __init__(self, api_client):
        self.client = api_client
        self.system_instruction = (
            "당신은 랜딩 페이지 분석 전문가입니다. 제공된 정보를 기반으로 정교한 JSON을 생성하세요. "
            "날짜는 반드시 YYYY-MM-DD 포맷을 준수해야 하며, 값이 불분명할 경우 해당 필드를 null로 비워두세요."
        )

    def get_json_schema(self):
        """Pydantic 모델의 스키마를 JSON 형태로 반환 (테스트 및 프롬프트용)"""
        return WeddingCpaData.model_json_schema()

    def analyze_image(self, image_path: str, api_basic_data: dict):
        print(f"[*] Gemini API 분석...")
        uploaded_file = self.client.files.upload(file=image_path)
        prompt = f"Data: {json.dumps(api_basic_data)}\nSchema: {json.dumps(self.get_json_schema())}\n이미지를 분석하여 JSON 생성."
        
        try:
            response = self.client.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=[prompt, uploaded_file],
                config=types.GenerateContentConfig(response_mime_type="application/json", system_instruction=self.system_instruction)
            )
            
            # 1차 JSON 파싱
            raw_json = json.loads(response.text)
            
            # 2차 Pydantic 데이터 검증 (Sanity Check)
            try:
                validated_data = WeddingCpaData(**raw_json)
                print(f"[✔] AI 데이터 검증 통과")
                # 검증된 데이터를 dict로 변환 (datetime.date 객체는 나중에 json 직렬화 시 처리 필요하여 .model_dump() 활용)
                return validated_data.model_dump(mode='json')
            except ValidationError as ve:
                print(f"[!] 데이터 검증 실패: {ve}")
                # 검증 실패 시 예외를 다시 던지거나, 로그 기록 후 실패 처리
                raise ValueError(f"AI 생성 데이터 유효성 검증 실패: {ve.errors()}")
        except Exception as e:
            print(f"[✘] analyze_image 도중 오류: {e}")
            raise e
        finally:
            try: self.client.files.delete(name=uploaded_file.name)
            except: pass

    def smart_merge(self, ai_data: dict, api_basic_data: dict, campaign_id: str, storage):
        ai_data["campaign_id"] = campaign_id
        ai_data["gather_name"] = api_basic_data.get("gather_name", ai_data.get("gather_name"))
        
        event = ai_data.setdefault("event_details", {}).setdefault("event", {})
        event["original_display_date"] = api_basic_data.get("ad_date")
        
        loc = ai_data.get("event_details", {}).setdefault("location", {})
        loc["original_address"] = api_basic_data.get("ad_location")
        loc["region_code"] = api_basic_data.get("region")

        # 시도/시군구 영문 명칭 추가 (Storage의 매핑 활용)
        sido_ko = loc.get("sido")
        sigungu_ko = loc.get("sigungu")
        loc["sido_en"] = storage.get_region_en(sido_ko)
        loc["sigungu_en"] = storage.get_district_en(sido_ko, sigungu_ko)

        ai_data["campaign_assets"] = {
            "target_url": api_basic_data.get("ad_url"),
            "mainvisual": api_basic_data.get("ad_mainvisual"),
            "thumbnail": api_basic_data.get("ad_thumbnail"),
            "thumbnail2": api_basic_data.get("ad_thumbnail2")
        }
        return ai_data


# ==========================================
# [영역 3: 저장 및 색인 관리 (Storage)]
# ==========================================
class WeddingDataStorage:
    def __init__(self, base_dir="data", mapping_path="lib/regionMapping.json"):
        self.base_dir = base_dir
        self.mapping = self._load_mapping(mapping_path)
        for sub in ["campaigns", "regions", "captures"]:
            os.makedirs(os.path.join(self.base_dir, sub), exist_ok=True)

    def _load_mapping(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_region_en(self, sido_ko):
        if not sido_ko: return "etc"
        if sido_ko in self.mapping:
            return self.mapping[sido_ko].get("en", "etc").lower()
        for key, info in self.mapping.items():
            if sido_ko in info.get("aliases", []) or key in sido_ko:
                return info.get("en", "etc").lower()
        return "etc"

    def get_district_en(self, sido_ko, sigungu_ko):
        if not sido_ko or not sigungu_ko: return sigungu_ko
        
        region_info = self.mapping.get(sido_ko)
        if not region_info:
            for key, info in self.mapping.items():
                if sido_ko in info.get("aliases", []) or key in sido_ko:
                    region_info = info
                    break
        
        if region_info and "districts" in region_info:
            districts = region_info["districts"]
            if sigungu_ko in districts:
                return districts[sigungu_ko].get("en", sigungu_ko).lower()
            for d_ko, d_info in districts.items():
                if d_ko in sigungu_ko or sigungu_ko in d_ko:
                    return d_info.get("en", sigungu_ko).lower()
        return sigungu_ko.lower()

    def _read_json(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _read_json_list(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []

    def _write_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _update_list(self, list_data, new_item):
        if not isinstance(list_data, list): return [new_item]
        cid = new_item.get("campaign_id")
        updated = False
        for i, item in enumerate(list_data):
            if item.get("campaign_id") == cid:
                list_data[i] = new_item
                updated = True
                break
        if not updated:
            list_data.append(new_item)
        return list_data

    def save_final_results(self, full_data: dict):
        cid = full_data.get("campaign_id")
        sido_ko = full_data.get("event_details", {}).get("location", {}).get("sido", "기타")
        region_en = self.get_region_en(sido_ko)

        campaign_path = os.path.join(self.base_dir, "campaigns", f"{cid}.json")
        self._write_json(campaign_path, full_data)

        summary = {
            "campaign_id": cid,
            "gather_name": full_data.get("gather_name"),
            "display_date": full_data.get("event_details", {}).get("event", {}).get("display_date"),
            "venue": full_data.get("event_details", {}).get("location", {}).get("venue"),
            "sido": sido_ko,
            "region_en": region_en,
            "thumbnail": full_data.get("campaign_assets", {}).get("thumbnail"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        for suffix, data in [("_index", summary), ("", full_data)]:
            path = os.path.join(self.base_dir, "regions", f"{region_en}{suffix}.json")
            current_list = self._read_json_list(path)
            self._write_json(path, self._update_list(current_list, data))

        for filename, data in [("all_index.json", summary), ("all.json", full_data)]:
            path = os.path.join(self.base_dir, filename)
            current_list = self._read_json_list(path)
            self._write_json(path, self._update_list(current_list, data))

        print(f"[✔] 데이터 저장 완료: {cid} (Region: {region_en})")

    def get_capture_path(self, campaign_id: str):
        return os.path.join(self.base_dir, "captures", f"{campaign_id}_capture.png")


# ==========================================
# [실행 메인 로직]
# ==========================================
async def run_single_campaign(api_basic_data: dict, collector, processor, storage, semaphore):
    async with semaphore:
        campaign_id = api_basic_data["campaign_id"]
        target_url = api_basic_data["ad_url"]
        print(f"\n[*] [{campaign_id}] 작업 시작...")

        try:
            screenshot_path = storage.get_capture_path(campaign_id)
            await collector.capture_full_page_mobile(target_url, screenshot_path)
            raw_ai_data = processor.analyze_image(screenshot_path, api_basic_data)
            final_data = processor.smart_merge(raw_ai_data, api_basic_data, campaign_id, storage)
            storage.save_final_results(final_data)
            print(f"[✔] [{campaign_id}] 처리 성공!")
        except Exception as e:
            print(f"[✘] [{campaign_id}] 처리 중 오류: {e}")

async def main_optimized():
    base_data_dir = "data"
    cache_path = os.path.join(base_data_dir, "api_cache.json")
    
    try:
        new_ads_dict = await WeddingApiLoader.fetch_all_ads()
        collector = WeddingDataCollector()
        processor = WeddingDataProcessor(client)
        storage = WeddingDataStorage(base_dir=base_data_dir)
        
        cached_ads_dict = storage._read_json(cache_path)

        target_ads = []
        for cid, new_data in new_ads_dict.items():
            if new_data != cached_ads_dict.get(cid):
                new_data["campaign_id"] = cid
                target_ads.append(new_data)

        if not target_ads:
            print("[*] 변경된 캠페인이 없습니다. 종료합니다.")
            return

        print(f"[*] 총 {len(target_ads)}건의 변경/신규 캠페인 수집 시작...")
        semaphore = asyncio.Semaphore(3)
        await collector.start()

        tasks = [run_single_campaign(ad_data, collector, processor, storage, semaphore) for ad_data in target_ads]
        await asyncio.gather(*tasks)

        storage._write_json(cache_path, new_ads_dict)
        print("\n[*] API 캐시 업데이트 완료.")

    except Exception as e:
        print(f"[✘] 메인 로직 오류: {e}")
    finally:
        if 'collector' in locals():
            await collector.stop()

if __name__ == "__main__":
    asyncio.run(main_optimized())