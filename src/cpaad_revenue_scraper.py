import os
import sys
import json
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 만약 src 폴더 안에 있다면 부모 디렉토리를 path에 추가
if BASE_DIR.endswith('src'):
    PARENT_DIR = os.path.dirname(BASE_DIR)
else:
    PARENT_DIR = BASE_DIR
    
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

try:
    from common.utils import load_env_variables
except ImportError:
    # 환경에 따라 import 방식이 다를 수 있음
    def load_env_variables(path): return {}

# .env 또는 .env.local 로드 시도
config = load_env_variables(PARENT_DIR)
if not config:
    # utils.py의 load_env_variables가 특정 파일만 볼 경우를 대비해 직접 시도 (옵션)
    try:
        from dotenv import dotenv_values
        config = dotenv_values(os.path.join(PARENT_DIR, ".env.local"))
    except:
        pass

MB_ID = config.get('MB_ID')
MB_PASSWORD = config.get('MB_PASSWORD')

LOGIN_ACTION_URL = 'https://www.cpaad.co.kr/bbs/login_check.php'
LIST_URL_TEMPLATE = 'https://www.cpaad.co.kr/sub/sub_ad_list.php?subNo=&category=05&page={page}'
DATA_FILE = os.path.join(PARENT_DIR, 'data', 'cpaad_revenue_data.json')

def get_total_pages(session, headers):
    """전체 페이지 수를 확인합니다."""
    res = session.get(LIST_URL_TEMPLATE.format(page=1), headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    paging = soup.select_one('.list_paging')
    if not paging:
        return 1
    
    # 맨 끝 버튼이나 마지막 숫자 링크 찾기
    links = paging.select('a')
    if not links:
        return 1
        
    last_link = links[-1]
    href = last_link.get('href', '')
    match = re.search(r'page=(\d+)', href)
    if match:
        return int(match.group(1))
    
    # 숫자들 중 가장 큰 값 찾기
    pages = [int(re.sub(r'[^\d]', '', d.text)) for d in paging.select('.active, div') if re.sub(r'[^\d]', '', d.text).isdigit()]
    return max(pages) if pages else 1

def parse_page(session, page, headers):
    """특정 페이지의 캠페인 데이터를 파싱합니다."""
    url = LIST_URL_TEMPLATE.format(page=page)
    print(f"페이지 파싱 중: {page}...")
    res = session.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    campaigns = []
    items = soup.select('div[style*="border-radius:10px"]')
    
    for item in items:
        try:
            # Campaign ID 추출 (ad_id 속성 값 찾기)
            # 주석 처리된 부분에서도 찾을 수 있도록 전체 HTML 문자열에서 regex로 검색
            item_html = str(item)
            ad_id_match = re.search(r'ad_id=["\']([^"\']+)["\']', item_html)
            
            if ad_id_match:
                campaign_id = ad_id_match.group(1)
            else:
                # ad_id를 찾지 못한 경우 기존처럼 idx를 fallback으로 사용
                detail_link = item.select_one('a[href*="sub_ad_detail.php?idx="]')
                if not detail_link:
                    continue
                href = detail_link.get('href')
                campaign_id = parse_qs(urlparse(href).query).get('idx', [None])[0]
            
            # Revenue 추출 (.no_style02 클래스 내의 금액)
            revenue_span = item.select_one('.no_style02')
            if revenue_span:
                revenue_text = revenue_span.get_text(strip=True)
                revenue = int(re.sub(r'[^\d]', '', revenue_text))
            else:
                revenue = 0
            
            # 캠페인 이름
            name_tag = item.select_one('a[href*="sub_ad_detail.php?idx="] span')
            if not name_tag:
                name_tag = item.select_one('th a span')
            
            name = name_tag.get_text(strip=True) if name_tag else "알 수 없음"
            
            if campaign_id:
                campaigns.append({
                    'campaign_id': campaign_id,
                    'name': name,
                    'revenue': revenue
                })
        except Exception as e:
            print(f"항목 파싱 오류: {e}")
            continue
            
    return campaigns

def main():
    if not MB_ID or not MB_PASSWORD:
        print("오류: 환경 변수에서 아이디나 비밀번호를 불러오지 못했습니다. (.env 또는 .env.local 확인)")
        return

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.cpaad.co.kr/bbs/login.php'
    }
    
    login_data = {
        'mb_id': MB_ID,
        'mb_password': MB_PASSWORD,
        'url': '%2Fsub%2Fsub_profit.php' 
    }
    
    print("로그인 시도 중...")
    session.post(LOGIN_ACTION_URL, data=login_data, headers=headers)
    
    # 전체 페이지 수 확인
    try:
        total_pages = get_total_pages(session, headers)
    except Exception as e:
        print(f"페이지 수 확인 실패: {e}")
        total_pages = 1
        
    print(f"총 {total_pages} 페이지를 발견했습니다.")
    
    all_campaigns = {}
    for page in range(1, total_pages + 1):
        try:
            page_data = parse_page(session, page, headers)
            for cp in page_data:
                all_campaigns[cp['campaign_id']] = {
                    'name': cp['name'],
                    'revenue': cp['revenue']
                }
        except Exception as e:
            print(f"{page} 페이지 로드 실패: {e}")
    
    if not all_campaigns:
        print("수집된 데이터가 없습니다. 로그인 상태나 HTML 구조를 확인하세요.")
        return

    # 테스트용 출력 (저장 전)
    print("\n--- 수집된 캠페인 데이터 (테스트 출력) ---")
    print(json.dumps(all_campaigns, ensure_ascii=False, indent=4))
    print("------------------------------------------\n")

    # 결과 저장
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_campaigns, f, ensure_ascii=False, indent=4)
    
    print(f"수집 완료: 총 {len(all_campaigns)}개의 캠페인 데이터를 {DATA_FILE}에 저장했습니다.")

if __name__ == "__main__":
    main()
