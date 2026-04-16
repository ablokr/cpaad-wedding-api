import json
import os
import re
from collections import defaultdict

def migrate_organizer_mapping():
    """
    기존의 organizerMapping.json 데이터를 새로운 '첫 번째 숫자 기준' 로직으로 
    재통합(Re-unify)하는 일회성 마이그레이션 스크립트입니다.
    """
    mapping_path = 'lib/organizerMapping.json'
    source_path = 'data/weddinggo/cpaad/ad_json_date.json'
    
    # 1. 기존 데이터 로드
    if not os.path.exists(mapping_path):
        print(f"[!] {mapping_path} 파일이 없습니다.")
        return
        
    with open(mapping_path, 'r', encoding='utf-8') as f:
        old_mapping = json.load(f)
        
    with open(source_path, 'r', encoding='utf-8') as f:
        ads_data = json.load(f).get('advertisements', {})
        all_campaign_ids = ads_data.keys()

    # 2. 새로운 로직으로 재분류
    new_mapping = {}
    
    # 기존에 등록된 이름 정보들을 cid별로 매핑 (상속용)
    cid_to_name = {}
    for oid, info in old_mapping.items():
        if "name" in info and info["name"]:
            for cid in info.get("campaigns", []):
                cid_to_name[cid] = info["name"]

    # 새로운 그룹 생성
    groups = defaultdict(list)
    for cid in all_campaign_ids:
        # 새로운 로직: 첫 번째 숫자가 나타나는 지점 앞까지 추출
        match = re.search(r'\d', cid)
        new_oid = cid[:match.start()] if match else cid
        groups[new_oid].append(cid)

    # 3. 새로운 매핑 객체 조립
    for oid, cids in groups.items():
        # 이 그룹에 속한 캠페인 중 기존에 이름이 있던 것이 있는지 확인
        possible_names = [cid_to_name[cid] for cid in cids if cid in cid_to_name]
        
        # 이름 결정 (가장 빈번하거나 첫 번째 이름을 선택)
        final_name = ""
        if possible_names:
            final_name = max(set(possible_names), key=possible_names.count)
        elif oid in old_mapping and old_mapping[oid].get("name"):
            # 기존 oid 키 자체가 새 oid와 일치하고 이름이 있는 경우
            final_name = old_mapping[oid]["name"]

        new_mapping[oid] = {
            "name": final_name,
            "campaigns": sorted(list(set(cids)))
        }

    # 4. Alias(에일리언스) 정보 보존 및 처리
    # 기존에 수동으로 alias_of를 설정했거나, 새 로직에서도 여전히 별개로 관리되어야 할 경우 대비
    for oid, info in old_mapping.items():
        if "alias_of" in info:
            # 타겟 주최사가 여전히 존재하는지 확인
            target = info["alias_of"]
            if target in new_mapping:
                # 에일리언스 복구
                new_mapping[oid] = {"alias_of": target}

    # 5. 결과 저장
    # 주최사 ID 기준으로 정렬
    sorted_mapping = {k: new_mapping[k] for k in sorted(new_mapping.keys())}
    
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"[✔] 마이그레이션 완료: {len(sorted_mapping)}개의 주최사 그룹으로 재편되었습니다.")

if __name__ == "__main__":
    migrate_organizer_mapping()
