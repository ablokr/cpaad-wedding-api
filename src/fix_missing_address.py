import os
import json
import asyncio
import sys

# 프로젝트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from api_loader import WeddingApiLoader

async def recover_and_fix_address():
    print("[*] 데이터 구조 긴급 복구 및 address 필드 적용 시작...")
    
    # 1. 원본 API 데이터 가져오기
    try:
        api_ads = await WeddingApiLoader.fetch_all_ads()
    except Exception as e:
        print(f"[✘] API 로드 실패: {e}")
        return

    # 2. 경로 설정
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    campaigns_dir = os.path.join(root_dir, "data", "campaigns")
    if not os.path.exists(campaigns_dir):
        print(f"[!] 경로 오류: {campaigns_dir}")
        return

    files = [f for f in os.listdir(campaigns_dir) if f.endswith(".json")]
    updated_count = 0

    for filename in files:
        camp_id = filename.replace(".json", "")
        file_path = os.path.join(campaigns_dir, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            continue

        api_data = api_ads.get(camp_id)
        if not api_data:
            continue

        # [수정 로직]
        modified = False

        # 1. 루트 레벨에 잘못 생성된 location 필드 삭제
        if "location" in data and "event_details" in data:
            del data["location"]
            modified = True

        # 2. 정확한 위치(event_details.location)에 address 추가
        if "event_details" in data and "location" in data["event_details"]:
            ad_location = api_data.get("ad_location", "")
            address = ad_location.split("||")[0].strip() if "||" in ad_location else ad_location
            
            data["event_details"]["location"]["address"] = address
            modified = True

        # 저장
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            updated_count += 1
            print(f"[✔] {camp_id} 복구 및 업데이트 완료")

    print(f"\n[✔] 개별 캠페인 복구 완료: {updated_count}개")

    # [확장] 4. 통합 파일 (all.json) 및 지역별 파일 (regions/*.json) 업데이트
    print("\n[*] 통합 파일(all.json) 및 지역별 데이터 동기화 시작...")
    
    # data 디렉토리 확보
    data_dir = os.path.dirname(campaigns_dir)
    regions_dir = os.path.join(data_dir, "regions")

    # 최신화된 개별 파일들을 다시 읽어서 메모리에 적재 (가장 확실한 소스)
    latest_campaigns = {}
    for filename in os.listdir(campaigns_dir):
        if filename.endswith(".json"):
            cid = filename.replace(".json", "")
            with open(os.path.join(campaigns_dir, filename), "r", encoding="utf-8") as f:
                latest_campaigns[cid] = json.load(f)

    # 4-1. all.json 업데이트
    all_json_path = os.path.join(data_dir, "all.json")
    if os.path.exists(all_json_path):
        # all.json은 보통 최신순 또는 특정 순서의 리스트이므로 순서를 유지하며 데이터만 교체
        try:
            with open(all_json_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            
            if isinstance(all_data, list):
                new_all_data = []
                for item in all_data:
                    cid = item.get("campaign_id")
                    if cid in latest_campaigns:
                        new_all_data.append(latest_campaigns[cid])
                    else:
                        new_all_data.append(item)
                
                with open(all_json_path, "w", encoding="utf-8") as f:
                    json.dump(new_all_data, f, ensure_ascii=False, indent=2)
                print("[✔] all.json 업데이트 완료")
        except Exception as e:
            print(f"[✘] all.json 업데이트 실패: {e}")

    # 4-2. regions/*.json 업데이트
    if os.path.exists(regions_dir):
        region_files = [f for f in os.listdir(regions_dir) if f.endswith(".json")]
        for r_file in region_files:
            r_path = os.path.join(regions_dir, r_file)
            try:
                with open(r_path, "r", encoding="utf-8") as f:
                    r_data = json.load(f)
                
                if isinstance(r_data, list):
                    new_r_data = []
                    for item in r_data:
                        cid = item.get("campaign_id")
                        if cid in latest_campaigns:
                            new_r_data.append(latest_campaigns[cid])
                        else:
                            new_r_data.append(item)
                    
                    with open(r_path, "w", encoding="utf-8") as f:
                        json.dump(new_r_data, f, ensure_ascii=False, indent=2)
                print(f"[✔] 지역 파일 업데이트 완료: {r_file}")
            except Exception as e:
                print(f"[✘] {r_file} 업데이트 실패: {e}")

    print("\n[✔] 모든 통합 데이터 파일 동기화 완료.")

if __name__ == "__main__":
    asyncio.run(recover_and_fix_address())
