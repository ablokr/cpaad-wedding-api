import os
import json
import glob

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
REVENUE_DATA_FILE = os.path.join(PARENT_DIR, 'data', 'cpaad_revenue_data.json')
CAMPAIGNS_DIR = os.path.join(PARENT_DIR, 'data', 'weddinggo', 'campaigns')
ALL_INDEX_FILE = os.path.join(PARENT_DIR, 'data', 'weddinggo', 'all_index.json')
ALL_DATA_FILE = os.path.join(PARENT_DIR, 'data', 'weddinggo', 'all.json')

def load_revenue_map():
    if not os.path.exists(REVENUE_DATA_FILE):
        print(f"[!] {REVENUE_DATA_FILE} 파일이 없습니다.")
        return {}
    with open(REVENUE_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_json_object(obj, revenue_map):
    """단일 JSON 객체에 revenue 정보를 주입합니다."""
    if isinstance(obj, dict) and 'campaign_id' in obj:
        cp_id = obj['campaign_id']
        if cp_id in revenue_map:
            # 기존 revenue 정보를 업데이트하거나 추가함
            obj['revenue'] = revenue_map[cp_id]['revenue']
            return True
    return False

def process_campaign_files(revenue_map):
    """개별 캠페인 JSON 파일들을 업데이트합니다."""
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
        # 데이터가 리스트인 경우 (보통 index 파일)
        if isinstance(data, list):
            for item in data:
                if update_json_object(item, revenue_map):
                    updated = True
        # 데이터가 딕셔너리이고 특정 키(예: 'campaigns')에 리스트가 있는 경우
        elif isinstance(data, dict):
            # 최상위 객체가 캠페인 정보를 포함할 경우
            if update_json_object(data, revenue_map):
                updated = True
            # 하위 키들을 탐색 (all.json 등 구조 대비)
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and update_json_object(item, revenue_map):
                            updated = True
                elif isinstance(value, dict):
                     if update_json_object(value, revenue_map):
                         updated = True

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] {os.path.basename(file_path)} 업데이트 완료.")
    except Exception as e:
        print(f"[!] {file_path} 처리 중 오류: {e}")

def main():
    print("[*] Revenue 데이터 병합 시작...")
    revenue_map = load_revenue_map()
    if not revenue_map:
        return

    # 1. 개별 캠페인 파일 업데이트
    process_campaign_files(revenue_map)
    
    # 2. 통합 인덱스 파일 업데이트
    process_aggregate_file(ALL_INDEX_FILE, revenue_map)
    
    # 3. 전체 데이터 파일 업데이트
    process_aggregate_file(ALL_DATA_FILE, revenue_map)
    
    print("[*] Revenue 데이터 병합 작업 종료.")

if __name__ == "__main__":
    main()
