import os
import json
import glob

# 경로 설정 (환경 변수 존중)
BASE_DATA_DIR = os.getenv("DATA_DIR", "data/weddinggo")
REVENUE_DATA_FILE = os.path.join(BASE_DATA_DIR, 'cpaad_revenue_data.json')
# 만약 base_dir에 없으면 루트의 data 폴더 확인 (폴백)
if not os.path.exists(REVENUE_DATA_FILE):
    REVENUE_DATA_FILE = 'data/cpaad_revenue_data.json'

CAMPAIGNS_DIR = os.path.join(BASE_DATA_DIR, 'campaigns')
ALL_INDEX_FILE = os.path.join(BASE_DATA_DIR, 'all_index.json')
ALL_DATA_FILE = os.path.join(BASE_DATA_DIR, 'all.json')
API_CACHE_FILE = os.path.join(BASE_DATA_DIR, 'api_cache.json')
PRE_AD_JSON_FILE = os.path.join(BASE_DATA_DIR, 'cpaad', 'pre_ad_json_date.json')

def load_revenue_map():
    if not os.path.exists(REVENUE_DATA_FILE):
        print(f"[!] {REVENUE_DATA_FILE} 파일이 없습니다.")
        return {}
    try:
        with open(REVENUE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] {REVENUE_DATA_FILE} 로드 실패: {e}")
        return {}

def update_json_object(obj, revenue_map, cp_id=None):
    """단일 JSON 객체에 revenue 및 idx 정보를 주입합니다."""
    if not isinstance(obj, dict):
        return False
    
    if cp_id is None:
        cp_id = obj.get('campaign_id')
    
    if not cp_id or cp_id not in revenue_map:
        return False
    
    updated = False
    revenue_info = revenue_map[cp_id]
    
    # 1. revenue 업데이트
    new_revenue = revenue_info.get('revenue')
    if new_revenue is not None and obj.get('revenue') != new_revenue:
        obj['revenue'] = new_revenue
        updated = True
        
    # 2. idx 업데이트 (campaign_id 위에 위치하도록 순서 조정)
    new_idx = revenue_info.get('idx')
    if new_idx is not None and obj.get('idx') != new_idx:
        if 'idx' in obj:
            obj['idx'] = new_idx
        else:
            # 순서 보장을 위해 새로 생성
            temp = {'idx': new_idx}
            temp.update(obj)
            obj.clear()
            obj.update(temp)
        updated = True
    
    return updated

def process_campaign_files(revenue_map):
    """개별 캠페인 JSON 파일들을 업데이트합니다."""
    if not os.path.exists(CAMPAIGNS_DIR): return
    files = glob.glob(os.path.join(CAMPAIGNS_DIR, '*.json'))
    updated_count = 0
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if update_json_object(data, revenue_map):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                updated_count += 1
        except Exception as e:
            print(f"[!] {file_path} 처리 중 오류: {e}")
    print(f"[*] 개별 캠페인 파일 {updated_count}개 업데이트 완료.")

def process_aggregate_file(file_path, revenue_map):
    """all_index.json 또는 all.json 같은 통합 파일들을 업데이트합니다."""
    if not os.path.exists(file_path):
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = False
        # 데이터가 리스트인 경우 (예: regions/*.json)
        if isinstance(data, list):
            for item in data:
                if update_json_object(item, revenue_map):
                    updated = True
        # 데이터가 딕셔너리인 경우
        elif isinstance(data, dict):
            # 1. items 키가 있는 경우 (all.json, all_index.json)
            if 'items' in data and isinstance(data['items'], list):
                for item in data['items']:
                    if update_json_object(item, revenue_map):
                        updated = True
            
            # 2. advertisements 키가 있는 경우 (pre_ad_json_date.json)
            elif 'advertisements' in data and isinstance(data['advertisements'], dict):
                for cid, ad in data['advertisements'].items():
                    if update_json_object(ad, revenue_map, cid):
                        updated = True
            
            # 3. 최상위가 캠페인 ID를 키로 가지는 경우 (api_cache.json)
            # (구분 방법: key가 캠페인 ID 패턴이고 value가 dict인 경우)
            else:
                for cid, item in data.items():
                    if isinstance(item, dict) and update_json_object(item, revenue_map, cid):
                        updated = True

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] {os.path.basename(file_path)} 업데이트 완료.")
    except Exception as e:
        print(f"[!] {file_path} 처리 중 오류: {e}")

def main():
    print(f"[*] Revenue/IDX 데이터 병합 시작 (Target: {BASE_DATA_DIR})...")
    revenue_map = load_revenue_map()
    if not revenue_map:
        return

    # 1. 개별 캠페인 파일 업데이트
    process_campaign_files(revenue_map)
    
    # 2. 주요 통합 파일 업데이트
    process_aggregate_file(ALL_INDEX_FILE, revenue_map)
    process_aggregate_file(ALL_DATA_FILE, revenue_map)
    process_aggregate_file(API_CACHE_FILE, revenue_map)
    process_aggregate_file(PRE_AD_JSON_FILE, revenue_map)
    
    # 3. 지역별 파일도 업데이트 (regions/*.json)
    region_files = glob.glob(os.path.join(BASE_DATA_DIR, 'regions', '*.json'))
    for rf in region_files:
        process_aggregate_file(rf, revenue_map)
    
    print("[*] Revenue/IDX 데이터 병합 작업 종료.")

if __name__ == "__main__":
    main()
