import os
import re
import platform
from playwright.async_api import async_playwright

class WeddingDataCollector:
    def __init__(self):
        self.playwright = None
        self.browser = None
        # ARM 아키텍처 감지 (aarch64, arm64 등)
        self._is_arm = platform.machine().lower() in ("aarch64", "arm64", "armv7l", "armv8l")

    async def start(self):
        """Playwright 브라우저 인스턴스를 초기화합니다.
        ARM 환경에서는 Chromium 대신 Firefox를 사용합니다 (호환성 우선).
        """
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            if self._is_arm:
                # ARM 환경: Firefox가 훨씬 안정적 (Chromium ARM 바이너리 미지원 이슈 회피)
                print("[*] [Collector] ARM 아키텍처 감지 → Firefox 브라우저 사용")
                try:
                    self.browser = await self.playwright.firefox.launch(headless=True)
                except Exception:
                    # Firefox도 실패할 경우 Chromium 시도 (시스템에 설치된 경우)
                    print("[!] [Collector] Firefox 실행 실패 → Chromium 폴백 시도")
                    self.browser = await self.playwright.chromium.launch(headless=True)
            else:
                # x86/x64 환경: Chromium 우선 사용
                self.browser = await self.playwright.chromium.launch(headless=True)

    async def stop(self):
        """브라우저 연결을 해제합니다."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def capture_full_page_mobile(self, url: str, output_path: str):
        """랜딩 페이지를 모바일 환경으로 설정하여 전체 화면을 스크린샷 캡처합니다."""
        print(f"[*] [Collector] 웹페이지 모바일 캡처 시작: {url}")
        if not self.browser:
            await self.start()

        # ARM Firefox에서는 devices 프리셋 대신 수동 설정
        # 왜: Firefox는 Playwright devices 프리셋과 호환이 안 될 수 있음
        if self._is_arm:
            context = await self.browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                device_scale_factor=1,
                is_mobile=True,
                has_touch=True
            )
        else:
            device_config = self.playwright.devices['iPhone 13']
            custom_config = dict(device_config)
            custom_config["device_scale_factor"] = 1 # 고화질보다는 텍스트 가독성 위주
            context = await self.browser.new_context(**custom_config)
        
        page = await context.new_page()
        
        try:
            print(f"[-] [Collector] [{url}] 페이지 로딩 중...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 무한 스크롤 대비 점진적 스크롤 (레이지 로딩 이미지 활성화를 위해)
            current_pos = 0
            step = 1000 
            while True:
                total_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate(f"window.scrollTo(0, {current_pos + step})")
                current_pos += step
                await page.wait_for_timeout(500) 
                if current_pos >= total_height: break
            
            await page.wait_for_timeout(2000) 
            
            print(f"[-] [Collector] [{url}] 이미지 저장 중...")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # 애니메이션 중지 및 전체 페이지 캡처
            await page.screenshot(path=output_path, full_page=True, animations="disabled", timeout=120000)
            print(f"[+] [Collector] 캡처 완료: {output_path}")

            # [추가] 주관사 실시간 이름 추출
            extracted_name = await self.extract_organizer_name(page)
            if extracted_name:
                print(f"[*] [Collector] 주관사 이름 추출 성공: {extracted_name}")
            
            return extracted_name
        finally:
            await page.close()
            await context.close()

    async def extract_organizer_name(self, page):
        """페이지 본문에서 주최사 이름을 추출합니다."""
        try:
            text_content = await page.evaluate("document.body.innerText")
            
            # 1. 메인 패턴: 개인정보의 수집/이용 문구 주변
            pattern = r"개인정보의?\s*수집\s*/?\s*이용\s*[:：\s]\s*(?:\(주\))?([\s\w가-힣]+)"
            match = re.search(pattern, text_content)
            
            extracted_name = ""
            if match:
                extracted_name = match.group(1).strip()
                # 줄바꿈이나 긴 공백에서 자르기
                extracted_name = re.split(r'[\n\r\t]|\s{2,}', extracted_name)[0].strip()
                # 불필요 관용구 제거
                extracted_name = re.sub(r'\(.*?\)|개인정보.*', '', extracted_name).strip()
            
            # 2. 폴백 패턴: (주)명칭 직접 찾기
            if not extracted_name or len(extracted_name) <= 1:
                alt_pattern = r"(?:\(주\))\s*([가-힣\w]+(?:웨딩|컨설팅|여행사|투어|페어|네트웍스)?)"
                alt_match = re.search(alt_pattern, text_content)
                if alt_match:
                    extracted_name = alt_match.group(1).strip()
            
            return extracted_name if extracted_name and len(extracted_name) > 1 else None
        except Exception:
            return None
