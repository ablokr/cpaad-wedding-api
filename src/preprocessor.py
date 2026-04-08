"""
원본 API 데이터에서 위치(시도/시군구)와 날짜를 사전 추출하는 전처리 모듈.

[목적]
- LLM 토큰 사용량 절감: AI에게 위치/날짜 분석을 맡기지 않음
- 데이터 정확도 향상: 원본 데이터 기반 파싱이 AI 추론보다 정확함
- 다른 앱(TypeScript)에서 검증된 parseLocationData 로직을 Python으로 이식
"""

import re
import json
import os
from datetime import datetime


class DataPreprocessor:
    def __init__(self, mapping_path="lib/regionMapping.json"):
        self.mapping = self._load_mapping(mapping_path)

        # API region 코드 → 시도 매핑 (1:1 확정)
        self.simple_region_map = {
            "capital": "서울",
            "gyeonggi": "경기",
            "incheon": "인천",
            "busan": "부산",
            "gangwon": "강원",
            "jeju": "제주",
        }

        # 광역 권역 → 세부 시도 후보군 (텍스트 단서로 좁힘)
        self.broad_region_map = {
            "chungcheong": ["대전", "세종", "충남", "충북"],
            "gyeongsang": ["대구", "울산", "경남", "경북"],
            "jeolla": ["광주", "전남", "전북"],
        }

    def _load_mapping(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ==========================================
    # [위치 파싱] — TS parseLocationData 이식
    # ==========================================

    def parse_location(self, location: str, title: str, ad_date: str, api_region: str) -> dict:
        """
        주소(location), 제목(title), 날짜내용(adDate), API 제공 지역(apiRegion)을 분석하여
        정확한 시도명과 시군구명을 추출합니다.
        """
        si_do = ""
        si_gun_gu = ""

        raw_location = location or ""
        title = title or ""
        ad_date = ad_date or ""
        
        # ── 0단계: '||' 구분자 처리 ──
        # 신규 API 형식: "도로명||지번||장소명"
        clean_location = raw_location
        if "||" in raw_location:
            parts = [p.strip() for p in raw_location.split("||") if p.strip()]
            if parts:
                clean_location = parts[0] # 첫 번째 섹션을 주소 파싱용으로 사용

        # ── 1단계: 주소에서 시도(si_do) 및 시군구(si_gun_gu) 직접 추출 ──
        if clean_location:
            parts = clean_location.strip().split()
            if parts:
                # 1-1. 시군구(si_gun_gu) 후보 탐색 (시도 명칭 제외 필터링)
                exclude_sido = [
                    "서울시", "특별시", "광역시", "경기도", "충청도", "전라도", "경상도", "강원도",
                    "특별자치시", "특별자치도"
                ]
                
                # 주소의 2~3번째 단어를 우선 검토 (예: "서울시 강남구", "경기도 안산시 상록구")
                candidate_parts = parts[1:3] if len(parts) > 1 else parts
                
                for p in candidate_parts:
                    if (p.endswith("구") or p.endswith("군") or (p.endswith("시") and len(p) > 1)) and not any(ex in p for ex in exclude_sido):
                        si_gun_gu = p
                        break
                
                # 1-2. 첫 번째 단어가 시도 명칭인지 확인
                for label, info in self.mapping.items():
                    search_terms = [label] + info.get("aliases", [])
                    if parts[0] in search_terms:
                        si_do = label
                        break

        # ── 2단계: 주소/제목/날짜에서 시도명(siDo) 유추 ──
        if not si_do:
            for label, info in self.mapping.items():
                search_terms = [label] + info.get("aliases", [])
                # 긴 이름부터 검색하여 정확도 향상 (예: "충청남도" → "충남")
                search_terms.sort(key=len, reverse=True)
                for term in search_terms:
                    if term in title or term in clean_location or term in ad_date:
                        si_do = label
                        break
                if si_do:
                    break

        # ── 3단계: 시군구 기반 역추적 + 부분 일치 검색 ──
        if not si_do:
            # 3-1. 추출된 siGunGu로 역조회
            if si_gun_gu:
                for label, info in self.mapping.items():
                    cities = info.get("cities", {})
                    if si_gun_gu in cities:
                        si_do = label
                        break

            # 3-2. 텍스트 내 시군구 명칭 부분 일치 (예: "전주" → "전주시" → 전북)
            if not si_do:
                text_pool = f"{title} {clean_location} {ad_date}"
                for label, info in self.mapping.items():
                    cities = info.get("cities", {})
                    for city_name in cities:
                        short_name = re.sub(r"[시군구]$", "", city_name)
                        if (
                            (len(short_name) > 1 and short_name in text_pool)
                            or city_name in text_pool
                        ):
                            si_do = label
                            if not si_gun_gu:
                                si_gun_gu = city_name
                            break
                    if si_do:
                        break

        # ── 4단계: API region 코드 매핑 (최후의 보루) ──
        if not si_do:
            if api_region in self.simple_region_map:
                si_do = self.simple_region_map[api_region]

            elif api_region in self.broad_region_map:
                candidates = self.broad_region_map[api_region]
                text_pool = f"{title} {location} {ad_date}"

                for candidate in candidates:
                    region_info = self.mapping.get(candidate)
                    if not region_info:
                        continue

                    # 시도명 또는 aliases로 직접 매칭
                    search_terms = [candidate] + region_info.get("aliases", [])
                    if any(term in text_pool for term in search_terms):
                        si_do = candidate
                        break

                    # 시군구명으로 역추적
                    cities = region_info.get("cities", {})
                    for city_name in cities:
                        short_name = re.sub(r"[시군구]$", "", city_name)
                        if city_name in text_pool or (len(short_name) > 1 and short_name in text_pool):
                            si_do = candidate
                            if not si_gun_gu:
                                si_gun_gu = city_name
                            break
                    if si_do:
                        break

                # 텍스트 단서가 전혀 없으면 첫 번째 후보를 폴백으로 사용
                if not si_do:
                    si_do = candidates[0]
            else:
                si_do = "기타"

        return {"sido": si_do, "sigungu": si_gun_gu}

    # ==========================================
    # [영문 변환] — regionMapping 기반
    # ==========================================

    def get_region_en(self, si_do: str) -> str:
        """시도명을 영문으로 변환"""
        if not si_do or si_do == "기타":
            return "etc"
        region_info = self.mapping.get(si_do)
        if region_info:
            return region_info.get("en", "etc").lower()
        # aliases를 통한 퍼지 매칭
        for key, info in self.mapping.items():
            if si_do in info.get("aliases", []) or key in si_do:
                return info.get("en", "etc").lower()
        return "etc"

    def get_city_slug(self, si_do: str, si_gun_gu: str) -> str:
        """시군구명을 영문 슬러그로 변환 (TS getCitySlug 이식)"""
        if not si_gun_gu:
            return ""
        region_info = self.mapping.get(si_do)
        if region_info and "cities" in region_info:
            # 정확 일치
            en_name = region_info["cities"].get(si_gun_gu)
            if en_name:
                return en_name.lower().replace(" ", "-")

            # 퍼지 매칭 (예: "안산시 상록구" → "안산시" 포함)
            for city_ko, city_en in region_info["cities"].items():
                if city_ko in si_gun_gu or si_gun_gu in city_ko:
                    return city_en.lower().replace(" ", "-")

        return si_gun_gu.lower()

    # ==========================================
    # [날짜 파싱]
    # ==========================================

    def parse_dates(self, date_str: str, api_data: dict = None) -> dict:
        """
        API에서 제공하는 start_date, end_date를 우선 사용합니다.
        제공되지 않을 경우에만 date_str에서 간단히 추출을 시도합니다.
        """
        api_data = api_data or {}
        api_start = api_data.get("start_date")
        api_end = api_data.get("end_date")

        # 1. API에서 제공하는 날짜가 있다면 최우선 적용
        if api_start and api_end:
            return {
                "start_date": api_start,
                "end_date": api_end,
                "display_date": date_str or "",
            }

        # 2. API 누락 시 폴백 (기존의 유연한 파싱 로직 유지)
        result = {
            "start_date": api_start,
            "end_date": api_end,
            "display_date": date_str or "",
        }
        if not date_str or "매주" in date_str:
            return result

        clean_str = re.sub(r"\([월화수목금토일]\)", "", date_str)
        clean_str = re.sub(r"\d{4}사전예약\w*", "", clean_str)

        date_patterns = [
            r"(\d{1,2})월\s*(\d{1,2})일",
            r"(\d{1,2})[./](\d{1,2})",
        ]

        found_dates = []
        ad_year = api_data.get("ad_year", "2026")
        year = int(ad_year) if ad_year and ad_year.isdigit() else 2026

        for pattern in date_patterns:
            matches = re.findall(pattern, clean_str)
            for m in matches:
                try:
                    month, day = int(m[0]), int(m[1])
                    dt = datetime(year, month, day)
                    found_dates.append(dt.strftime("%Y-%m-%d"))
                except:
                    continue

        if found_dates:
            unique_dates = sorted(list(set(found_dates)))
            if not result["start_date"]: result["start_date"] = unique_dates[0]
            if not result["end_date"]:
                result["end_date"] = unique_dates[-1] if len(unique_dates) >= 2 else unique_dates[0]

        return result

    # ==========================================
    # [장소명 추출]
    # ==========================================

    def extract_venue(self, address: str) -> str:
        """
        주소 문자열에서 장소명(venue)만 분리하여 추출합니다.
        신규 '||' 형식을 최우선으로 대응하되 가이드 텍스트(출구/도보)는 제거합니다.
        """
        if not address:
            return ""

        # 가이드/교통 정보 키워드 (제거 대상)
        noise_keywords = ["도보", "출구", "지하철", "번출구", "이용 권장"]

        # 1. '||' 구분자가 있는 경우
        if "||" in address:
            parts = [p.strip() for p in address.split("||") if p.strip()]
            # 뒤에서부터 탐색하여 노이즈가 아닌 첫 번째 섹션을 장소로 선택
            for part in reversed(parts):
                if not any(noise in part for noise in noise_keywords):
                    # 괄호 지번 정교하게 제거: (동/로/번지 숫자) 형태만 제거하고 일반 설명은 유지
                    clean_part = re.sub(r"\([^)]+[동가동리-]\s*\d+[^)]*\)", "", part).strip()
                    if clean_part:
                        return clean_part
            # 노이즈만 있다면 마지막 섹션이라도 반환 (폴백)
            return parts[-1]

        # 2. 괄호로 된 지번 주소 이후 텍스트 추출 (구형 호환)
        match = re.search(r"\([^)]+[동가동리-]\s*\d+[^)]*\)\s*(.+)$", address)
        if match:
            venue = match.group(1).strip()
            if venue:
                return venue

        # 3. 상세 단위(층/호/로/길) 뒤 텍스트 (구형 호환)
        parts = address.split()
        venue_candidates = []
        capture = False
        for part in parts:
            if capture:
                venue_candidates.append(part)
                continue
            if re.search(r"\d+(번지|길|로|층|호|F)$", part) or re.search(r"^\d+\-\d+(\-\d+)?$", part) or re.search(r"^\d+$", part):
                capture = True
        
        if venue_candidates:
            v_str = " ".join(venue_candidates).strip()
            if v_str and not any(noise in v_str for noise in noise_keywords):
                return v_str

        return " ".join(parts[-2:]) if len(parts) >= 2 else address

    # ==========================================
    # [통합 전처리 엔트리포인트]
    # ==========================================

    def preprocess(self, api_data: dict) -> dict:
        """
        원본 API 데이터에서 전처리 가능한 모든 정보를 추출합니다.
        AI 분석 전에 호출하여 토큰 사용량을 줄이고 데이터 정확도를 높입니다.
        """
        location_str = api_data.get("ad_location", "")
        title = api_data.get("gather_name", "")
        ad_date = api_data.get("ad_date", "")
        api_region = api_data.get("region", "")

        # 위치 파싱
        loc = self.parse_location(location_str, title, ad_date, api_region)
        sido = loc["sido"]
        sigungu = loc["sigungu"]

        # 영문 변환
        sido_en = self.get_region_en(sido)
        sigungu_en = self.get_city_slug(sido, sigungu)

        # 장소명(Venue) 추출
        venue = self.extract_venue(location_str)

        # 날짜 파싱 (API 제공 데이터 우선 사용)
        dates = self.parse_dates(ad_date, api_data)

        print(f"[-] [Preprocessor] 위치: {sido}({sido_en}) {sigungu}({sigungu_en}) | 장소: {venue} | 날짜: {dates.get('start_date', '?')}~{dates.get('end_date', '?')}")

        # 주소 추출 (|| 구분자 기준 첫 번째 섹션)
        address_part = location_str.split("||")[0].strip() if "||" in location_str else location_str

        return {
            "location": {
                "sido": sido,
                "sido_en": sido_en,
                "sigungu": sigungu,
                "sigungu_en": sigungu_en,
                "address": address_part,
                "venue": venue,
            },
            "dates": dates,
        }
