import os
import json
import time
import re

class WeddingDataStorage:
    def __init__(self, base_dir="data/weddinggo", capture_dir="data/captures", mapping_path="lib/regionMapping.json"):
        self.base_dir = base_dir
        self.capture_dir = capture_dir
        self.mapping = self._load_mapping(mapping_path)
        
        # 1. 필수 데이터 디렉토리 구성 (base_dir 하위)
        for sub in ["campaigns", "regions", "cpaad"]:
            os.makedirs(os.path.join(self.base_dir, sub), exist_ok=True)
            
        # 2. 캡처 디렉토리 구성 (별도 관리)
        os.makedirs(self.capture_dir, exist_ok=True)

    def _load_mapping(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_region_en(self, sido_ko):
        """시도(KO) 이름을 영어 코드로 변환 (lib/regionMapping.json 참조)"""
        if not sido_ko: return "etc"
        if sido_ko in self.mapping:
            return self.mapping[sido_ko].get("en", "etc").lower()
        for key, info in self.mapping.items():
            if sido_ko in info.get("aliases", []) or key in sido_ko:
                return info.get("en", "etc").lower()
        return "etc"

    def get_district_en(self, sido_ko, sigungu_ko):
        """시군구(KO) 이름을 영어 이름으로 변환 (regionMapping.json의 cities 키 사용)"""
        if not sido_ko or not sigungu_ko: return sigungu_ko
        
        # 시도 정보 조회 (직접 매칭 → aliases 퍼지 매칭)
        region_info = self.mapping.get(sido_ko)
        if not region_info:
            for key, info in self.mapping.items():
                if sido_ko in info.get("aliases", []) or key in sido_ko:
                    region_info = info
                    break
        
        # [수정] "districts" → "cities" : regionMapping.json의 실제 키와 일치시킴
        if region_info and "cities" in region_info:
            cities = region_info["cities"]
            
            # 1. 정확 일치 (예: "강남구" → "Gangnam")
            if sigungu_ko in cities:
                return cities[sigungu_ko].lower()
            
            # 2. 퍼지 매칭 (예: "안산시 상록구" → "안산시" 포함 → "Ansan")
            for city_ko, city_en in cities.items():
                if city_ko in sigungu_ko or sigungu_ko in city_ko:
                    return city_en.lower()
        
        return sigungu_ko.lower()

    def read_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError):
                # 빈 파일이거나 손상된 경우 빈 딕셔너리로 복구
                print(f"[!] [Storage] {path} 파싱 실패 (빈 파일 또는 손상). 빈 캐시로 초기화합니다.")
                return {}
        return {}

    def read_json_list(self, path):
        """배열 형태 [] 또는 통계 포함 객체 {"items": []} 형태 모두 지원하도록 확장"""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "items" in data:
                    return data["items"]
                return []
        return []

    def _wrap_with_stats(self, items):
        """리스트를 받아 통계 정보가 포함된 표준 구조 객체로 변환"""
        regions = set()
        districts = set()

        for item in items:
            # 1. 시도(Region) 추출
            r_en = item.get("region_en")
            if not r_en:
                sido_ko = item.get("sido") or item.get("event_details", {}).get("location", {}).get("sido")
                if sido_ko:
                    r_en = self.get_region_en(sido_ko)
            if r_en: regions.add(r_en)

            # 2. 시군구(District) 추출
            sigungu = item.get("sigungu") or item.get("event_details", {}).get("location", {}).get("sigungu")
            if sigungu: districts.add(sigungu)

        return {
            "stats": {
                "total_count": len(items),
                "region_count": len(regions),
                "district_count": len(districts),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "items": items
        }

    def write_json(self, path, data):
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
        """최종 분석 데이터를 개별 캠페인 파일, 지역별 색인, 전체 색인에 저장합니다."""
        cid = full_data.get("campaign_id")
        sido_ko = full_data.get("event_details", {}).get("location", {}).get("sido", "기타")
        region_en = self.get_region_en(sido_ko)

        # 1. 개별 캠페인 상세 저장
        campaign_path = os.path.join(self.base_dir, "campaigns", f"{cid}.json")
        self.write_json(campaign_path, full_data)

        # 2. 요약 정보 생성 (색인용)
        summary = {
            "campaign_id": cid,
            "gather_name": full_data.get("gather_name"),
            "display_date": full_data.get("event_details", {}).get("event", {}).get("display_date"),
            "venue": full_data.get("event_details", {}).get("location", {}).get("venue"),
            "sido": sido_ko,
            "sigungu": full_data.get("event_details", {}).get("location", {}).get("sigungu"),
            "region_en": region_en,
            "thumbnail": full_data.get("campaign_assets", {}).get("thumbnail"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 3. 지역별 색인 업데이트
        for suffix, data in [("_index", summary), ("", full_data)]:
            path = os.path.join(self.base_dir, "regions", f"{region_en}{suffix}.json")
            current_list = self.read_json_list(path)
            self.write_json(path, self._update_list(current_list, data))

        # 4. 전체 색인 업데이트 (통계 포함 객체 구조)
        for filename, data in [("all_index.json", summary), ("all.json", full_data)]:
            path = os.path.join(self.base_dir, filename)
            current_list = self.read_json_list(path)
            updated_list = self._update_list(current_list, data)
            # 전체 데이터는 항상 통계와 함께 래핑하여 저장
            self.write_json(path, self._wrap_with_stats(updated_list))

        print(f"[✔] [Storage] 데이터 저장 완료: {cid} (Region: {region_en})")

    def get_capture_path(self, campaign_id: str):
        """해당 캠페인의 스크린샷 저장 경로 반환 (shared capture_dir 사용)"""
        return os.path.join(self.capture_dir, f"{campaign_id}_capture.png")

    def is_campaign_exists(self, campaign_id: str):
        """해당 캠페인의 최종 결과 파일(JSON)이 이미 존재하는지 확인"""
        campaign_path = os.path.join(self.base_dir, "campaigns", f"{campaign_id}.json")
        return os.path.exists(campaign_path)

    def update_api_cache(self, cid, data):
        """단일 캠페인 수집 성공 시 api_cache.json 파일을 실시간으로 업데이트합니다."""
        cache_path = os.path.join(self.base_dir, "api_cache.json")
        
        # 최신 파일 읽기
        if not os.path.exists(cache_path):
            current_cache = {}
        else:
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    current_cache = json.load(f)
            except:
                current_cache = {}
        
        # 해당 캠페인만 업데이트 후 즉시 저장
        current_cache[cid] = data
        self.write_json(cache_path, current_cache)

    def save_raw_api_data(self, data):
        """API 원본 응답 데이터를 data/.../cpaad/ad_json_date.json에 저장합니다."""
        path = os.path.join(self.base_dir, "cpaad", "ad_json_date.json")
        self.write_json(path, data)
        print(f"[✔] [Storage] API 원본 백업 완료: {path}")

    def save_preprocessed_api_data(self, data):
        """API 응답 데이터를 전처리하여 data/.../cpaad/pre_ad_json_date.json에 저장합니다."""
        path = os.path.join(self.base_dir, "cpaad", "pre_ad_json_date.json")
        self.write_json(path, data)
        print(f"[✔] [Storage] API 대상 전처리 백업 완료: {path}")

    def delete_campaign_data(self, cid):
        """특정 캠페인 관련 데이터(JSON, 이미지, 검색 색인 등)를 모두 삭제합니다."""
        # 1. 개별 캠페인 파일 삭제 시도 및 지역 정보 파악
        campaign_path = os.path.join(self.base_dir, "campaigns", f"{cid}.json")
        region_en = None
        if os.path.exists(campaign_path):
            try:
                with open(campaign_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sido_ko = data.get("event_details", {}).get("location", {}).get("sido")
                    region_en = self.get_region_en(sido_ko)
                os.remove(campaign_path)
            except:
                pass

        # 2. 캡처 이미지 삭제
        capture_path = self.get_capture_path(cid)
        if os.path.exists(capture_path):
            try:
                os.remove(capture_path)
            except:
                pass

        # 3. 색인 파일 업데이트 (all.json, all_index.json, region.json, region_index.json)
        def _remove_from_list(list_data, target_cid):
            return [item for item in list_data if item.get("campaign_id") != target_cid]

        # 3-1. 전체 색인에서 제거
        for filename in ["all.json", "all_index.json"]:
            path = os.path.join(self.base_dir, filename)
            if os.path.exists(path):
                current_list = self.read_json_list(path)
                new_list = _remove_from_list(current_list, cid)
                if len(current_list) != len(new_list):
                    # 삭제 후에도 통계 갱신하여 저장
                    self.write_json(path, self._wrap_with_stats(new_list))

        # 3-2. 지역 색인에서 제거
        if region_en:
            for suffix in ["", "_index"]:
                path = os.path.join(self.base_dir, "regions", f"{region_en}{suffix}.json")
                if os.path.exists(path):
                    current_list = self.read_json_list(path)
                    new_list = _remove_from_list(current_list, cid)
                    if len(current_list) != len(new_list):
                        self.write_json(path, new_list)
        
        print(f"[!] [Storage] 데이터 삭제 완료: {cid}")

    def update_organizer_mapping(self, advertisements: dict):
        """
        새로운 캠페인과 주최사를 lib/organizerMapping.json에 증분(Incremental) 방식으로 추가합니다.
        기존에 존재하던 주최사 명칭(name)은 절대 덮어쓰지 않습니다.
        """
        # 프로젝트 루트 경로 계산 (src/storage.py 기준 한 단계 위)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mapping_dir = os.path.join(root_dir, "lib")
        mapping_path = os.path.join(mapping_dir, "organizerMapping.json")
        
        # 1. 기존 매핑 파일 로드
        mapping = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            except Exception as e:
                print(f"[!] [Storage] 매핑 파일 로드 실패 (새로 생성 가능성): {e}")
                mapping = {}
        
        updated = False
        
        # 1.5 전체 매핑에서 이미 할당된 캠페인 ID 세트 생성 (중복 할당 방지 및 수동 이동 존중)
        all_mapped_campaigns = set()
        for org_info in mapping.values():
            all_mapped_campaigns.update(org_info.get("campaigns", []))

        # 2. 신규 광고 순회하며 매핑 데이터 조립
        for campaign_id in advertisements.keys():
            # 이미 어딘가에 할당되어 있다면 (사용자가 수동으로 옮긴 경우 포함) 건너뜀
            if campaign_id in all_mapped_campaigns:
                continue

            # [수정] organizer_id 추출: 첫 번째 숫자가 나타나는 지점 앞까지 취함
            # 예: revewedding01tw -> revewedding, weddingdc04A -> weddingdc
            match = re.search(r'\d', campaign_id)
            candidate_id = campaign_id[:match.start()] if match else campaign_id
            
            # [신규] 에일리언스(Alias) 해결 로직
            # 해당 ID가 이미 존재하고 다른 ID를 가리키고 있다면(alias_of), 대상 ID를 변경
            target_id = candidate_id
            if candidate_id in mapping and "alias_of" in mapping[candidate_id]:
                target_id = mapping[candidate_id]["alias_of"]
                print(f"[*] [Storage] 에일리언스 해결: {candidate_id} -> {target_id}")

            # 주최사 자체가 새로 감지된 경우
            if target_id not in mapping:
                mapping[target_id] = {
                    "name": "",
                    "campaigns": []
                }
                updated = True
                print(f"[*] [Storage] 신규 주최사 감지: {target_id}")
            
            # 대상 주최사가 다른 ID를 가리키는 에일리언스인 경우 (재귀적으로 해결)
            # (매핑 파일 구조상 한 단계만 있는 것을 권장하지만, 안전을 위해 루프 방지 처리하며 확인)
            safety_limit = 5
            while "alias_of" in mapping[target_id] and safety_limit > 0:
                target_id = mapping[target_id]["alias_of"]
                safety_limit -= 1

            # 해당 캠페인 ID 추가 (위에서 중복 체크를 했으므로 여기서는 안전하게 추가 가능)
            if campaign_id not in mapping[target_id]["campaigns"]:
                mapping[target_id]["campaigns"].append(campaign_id)
                all_mapped_campaigns.add(campaign_id)
                updated = True
                print(f"[*] [Storage] 신규 캠페인 매핑 추가: {target_id} -> {campaign_id}")

        # 3. 변경 사항이 있을 때만 저장
        if updated:
            # [추가] 이름 중복 기반 자동 통합 (reveweddingE -> revewedding 등)
            name_merged = self._merge_organizers_by_name(mapping)
            if name_merged: updated = True

            # 주최사 ID 기준으로 정렬하여 가독성 유지
            sorted_mapping = {k: mapping[k] for k in sorted(mapping.keys())}
            os.makedirs(mapping_dir, exist_ok=True)
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
            print(f"[✔] [Storage] organizerMapping.json 업데이트 완료.")
            # [추가] data 폴더로 복사
            self._copy_organizer_mapping_to_data()
        else:
            print("[*] [Storage] organizerMapping.json 변경 사항 없음.")

    def _merge_organizers_by_name(self, mapping: dict) -> bool:
        """
        동일한 주관사 이름(name)을 가진 항목들을 가장 짧은 키(Original)로 통합합니다.
        병합된 항목들은 alias_of로 변경됩니다.
        """
        name_groups = {}
        
        # 1. 이름별로 그룹화 (alias가 아닌 실제 데이터가 있는 것들만)
        for oid, info in mapping.items():
            name = info.get("name")
            if name and "alias_of" not in info:
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(oid)
        
        updated = False
        for name, oids in name_groups.items():
            if len(oids) <= 1:
                continue
            
            # 2. 대표 키(가장 짧은 키) 선정
            primary_id = min(oids, key=len)
            
            for oid in oids:
                if oid == primary_id:
                    continue
                
                # 3. 캠페인 리스트 통합
                extra_campaigns = mapping[oid].get("campaigns", [])
                if "campaigns" not in mapping[primary_id]:
                    mapping[primary_id]["campaigns"] = []
                
                for cid in extra_campaigns:
                    if cid not in mapping[primary_id]["campaigns"]:
                        mapping[primary_id]["campaigns"].append(cid)
                        updated = True
                
                # 4. 병합된 키를 에일리언스로 전환
                mapping[oid] = {
                    "alias_of": primary_id
                }
                updated = True
                print(f"[*] [Storage] 이름 중복 통합: {oid} -> {primary_id} ({name})")
        
        return updated

    def update_organizer_name(self, campaign_id: str, brand_name: str):
        """특정 캠페인의 주관사 이름을 실시간으로 업데이트합니다 (이름이 없는 경우에만)."""
        mapping_path = os.path.join("lib", "organizerMapping.json")
        if not os.path.exists(mapping_path): return

        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            # 1. 주관사 ID 도출 (첫 번째 숫자 기준)
            match = re.search(r'\d', campaign_id)
            candidate_id = campaign_id[:match.start()] if match else campaign_id
            
            # 2. 에일리언스(Alias) 해결
            target_id = candidate_id
            safety_limit = 5
            while "alias_of" in mapping.get(target_id, {}) and safety_limit > 0:
                target_id = mapping[target_id]["alias_of"]
                safety_limit -= 1

            # 3. 이름 업데이트 (비어있거나 유효하지 않은 경우만)
            if target_id in mapping:
                current_name = mapping[target_id].get("name", "")
                if not current_name or len(current_name) <= 1:
                    mapping[target_id]["name"] = brand_name
                    
                    # [추가] 이름 업데이트 즉시 자동 통합 수행
                    self._merge_organizers_by_name(mapping)
                    
                    with open(mapping_path, 'w', encoding='utf-8') as f:
                        # 정렬하여 정돈된 상태로 저장
                        sorted_mapping = {k: mapping[k] for k in sorted(mapping.keys())}
                        json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
                    print(f"[✔] [Storage] 주관사 이름 실시간 업데이트 및 자동 통합 완료: {target_id} -> {brand_name}")
                    # [추가] data 폴더로 복사
                    self._copy_organizer_mapping_to_data()
        except Exception as e:
            print(f"[!] [Storage] 주관사 이름 업데이트 중 오류: {e}")

    def get_organizer_name(self, campaign_id: str) -> str:
        """campaign_id에 해당하는 주관사 이름을 반환합니다."""
        mapping_path = os.path.join("lib", "organizerMapping.json")
        if not os.path.exists(mapping_path): return ""

        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            # 1. 역방향 검색 (campaigns 리스트에 포함되어 있는지 확인)
            for oid, info in mapping.items():
                if "campaigns" in info and campaign_id in info["campaigns"]:
                    # alias 해결
                    target_id = oid
                    safety_limit = 5
                    while "alias_of" in mapping.get(target_id, {}) and safety_limit > 0:
                        target_id = mapping[target_id]["alias_of"]
                        safety_limit -= 1
                    return mapping.get(target_id, {}).get("name", "")

            # 2. campaign_id에서 ID 추출하여 검색 (새로운 캠페인 대비)
            match = re.search(r'\d', campaign_id)
            candidate_id = campaign_id[:match.start()] if match else campaign_id
            
            target_id = candidate_id
            safety_limit = 5
            while "alias_of" in mapping.get(target_id, {}) and safety_limit > 0:
                target_id = mapping[target_id]["alias_of"]
                safety_limit -= 1
            
            return mapping.get(target_id, {}).get("name", "")
        except:
            return ""

    def _copy_organizer_mapping_to_data(self):
        """lib/organizerMapping.json 파일을 data 폴더로 복사합니다."""
        src_path = os.path.join("lib", "organizerMapping.json")
        dst_path = os.path.join("data", "organizerMapping.json")
        
        if not os.path.exists(src_path):
            return
            
        try:
            import shutil
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"[✔] [Storage] organizerMapping.json을 {dst_path}로 복사했습니다.")
        except Exception as e:
            print(f"[!] [Storage] organizerMapping.json 복사 실패: {e}")

