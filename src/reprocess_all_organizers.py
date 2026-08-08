import os
import json
import re
import sys

# 프로젝트 루트를 path에 추가하여 src 모듈 로드 가능하게 함
sys.path.append(os.getcwd())

from src.storage import WeddingDataStorage

def reprocess_all_organizers():
    """
    기존에 생성된 모든 JSON 데이터를 순회하며 
    organizer_name과 structured_data.event_schema.organizer를 추가합니다.
    """
    # 1. 초기화
    # DATA_DIR 환경변수가 있으면 사용, 없으면 기본값들 순회
    datasets = ["weddinggo", "weddingExpo"]
    
    for dataset in datasets:
        base_dir = f"data/{dataset}"
        if not os.path.exists(base_dir):
            continue
            
        print(f"[*] 데이터셋 처리 중: {dataset}")
        storage = WeddingDataStorage(base_dir=base_dir)
        
        # 2. 모든 캠페인 상세 파일 처리 (data/dataset/campaigns/*.json)
        campaign_dir = os.path.join(base_dir, "campaigns")
        if os.path.exists(campaign_dir):
            for filename in os.listdir(campaign_dir):
                if not filename.endswith(".json"):
                    continue
                
                path = os.path.join(campaign_dir, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except:
                        continue
                
                cid = data.get("campaign_id")
                if not cid:
                    continue
                    
                org_name = storage.get_organizer_name(cid)
                if org_name:
                    data["organizer_name"] = org_name
                    
                    # event_schema 업데이트
                    if "structured_data" in data and "event_schema" in data["structured_data"]:
                        schema = data["structured_data"]["event_schema"]
                        if isinstance(schema, dict):
                            schema["organizer"] = {
                                "@type": "Organization",
                                "name": org_name,
                                "url": data.get("campaign_assets", {}).get("target_url", "")
                            }
                            s_date = data.get("event_details", {}).get("event", {}).get("start_date")
                            e_date = data.get("event_details", {}).get("event", {}).get("end_date")
                            if s_date: schema["startDate"] = s_date
                            if e_date: schema["endDate"] = e_date
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  [OK] {campaign_dir} 업데이트 완료")

        # 3. 색인 및 전체 파일 처리 (all.json, all_index.json, regions/*.json)
        # 처리할 리스트 파일 목록
        list_files = [
            os.path.join(base_dir, "all.json"),
            os.path.join(base_dir, "all_index.json")
        ]
        
        # 지역별 파일 추가
        region_dir = os.path.join(base_dir, "regions")
        if os.path.exists(region_dir):
            for filename in os.listdir(region_dir):
                if filename.endswith(".json"):
                    list_files.append(os.path.join(region_dir, filename))
        
        for path in list_files:
            if not os.path.exists(path):
                continue
                
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                except:
                    continue
            
            is_wrapped = isinstance(content, dict) and "items" in content
            items = content["items"] if is_wrapped else content
            
            if not isinstance(items, list):
                continue
                
            updated_count = 0
            for item in items:
                cid = item.get("campaign_id")
                if not cid:
                    continue
                    
                org_name = storage.get_organizer_name(cid)
                if org_name:
                    item["organizer_name"] = org_name
                    
                    # 상세 데이터인 경우(all.json 등) event_schema 업데이트
                    if "structured_data" in item and "event_schema" in item["structured_data"]:
                        schema = item["structured_data"]["event_schema"]
                        if isinstance(schema, dict):
                            schema["organizer"] = {
                                "@type": "Organization",
                                "name": org_name,
                                "url": item.get("campaign_assets", {}).get("target_url", "")
                            }
                            s_date = item.get("event_details", {}).get("event", {}).get("start_date")
                            e_date = item.get("event_details", {}).get("event", {}).get("end_date")
                            if s_date: schema["startDate"] = s_date
                            if e_date: schema["endDate"] = e_date
                    updated_count += 1
            
            if updated_count > 0:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"  [OK] {path} 업데이트 완료 ({updated_count}건)")

    # 4. 최종적으로 매핑 파일 한번 더 복사 (최신화 확인)
    try:
        import shutil
        src_mapping = "lib/organizerMapping.json"
        dst_mapping = "data/organizerMapping.json"
        if os.path.exists(src_mapping):
            shutil.copy2(src_mapping, dst_mapping)
            print(f"[*] {dst_mapping} 최신화 완료")
    except:
        pass

if __name__ == "__main__":
    reprocess_all_organizers()
