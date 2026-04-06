# 👰 Wedding CPA Data Pipeline (AI-Powered)

웨딩 박람회 및 광고 데이터를 수집하고, **Gemini AI**를 활용하여 고품질의 구조화된 데이터를 추출하는 데이터 파이프라인 프로젝트입니다.

---

## 🚀 주요 기능 (Key Features)

1.  **실시간 데이터 수집 (Collector)**
    - `cpaad.co.kr` API를 통해 광고 캠페인 정보를 수집합니다.
    - `Playwright`를 사용하여 모바일 환경의 랜딩 페이지 전체 스크린샷을 확보합니다.
2.  **AI 이미지 분석 (Processor)**
    - **Gemini 1.5/2.0 API**를 통해 캡처된 이미지를 분석합니다.
    - SEO 메타데이터, 마케팅 헤드라인, 혜택, 이벤트 일정 및 장소 정보를 정밀하게 추출합니다.
3.  **데이터 검증 레이어 (Sanity Check)**
    - **Pydantic** 모델링을 도입하여 AI가 생성한 데이터의 형식을 검증합니다.
    - 필수 필드 누락 및 날짜 형식(`YYYY-MM-DD`)을 체크하여 불량 데이터 유입을 사단합니다.
4.  **자동화된 데이터 저장 (Storage)**
    - 지역별(sido), 캠페인별 JSON 파일로 자동 분류 및 색인화합니다.
    - API 캐시 메커니즘을 통해 변경된 캠페인만 선별적으로 수집하여 토큰 비용을 최적화합니다.

---

## 🛠 기술 스택 (Tech Stack)

- **Language:** Python 3.11+
- **Core Libraries:**
    - `pydantic`: 데이터 모델링 및 유효성 검사
    - `google-genai`: Gemini AI 분석 (Vision)
    - `playwright`: 모바일 웹캡처
    - `httpx` & `asyncio`: 비동기 API 요청 및 작업 처리
- **Storage:** Local File-based JSON Database

---

## 📂 프로젝트 구조 (Directory Structure)

```text
wedding-cpa-api/
├── src/
│   └── get_cpaad_wedding_api.py  # 메인 파이프라인 소스 코드
├── lib/
│   └── regionMapping.json       # 시도/시군구 영문 매핑 정보
├── data/
│   ├── campaigns/               # 상세 캠페인 JSON 데이터
│   ├── regions/                 # 지역별 색인 데이터
│   ├── captures/                # 랜딩 페이지 PNG 캡처본
│   └── api_cache.json           # 수집 상태 관리 캐시
└── .github/workflows/           # GitHub Actions 자동 수집 설정
```

---

## ⚙️ 실행 환경 설정 (Setup)

### 1. 환경 변수 설정
프로젝트 루트에 `.env` 또는 `.env.local` 파일을 생성하고 아래 키를 입력하세요.

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. 의존성 설치
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. 수집 실행
```powershell
python src/get_cpaad_wedding_api.py
```

---

## 💎 데이터 검증 프로세스 (Data Validation)

본 프로젝트는 AI 응답의 불확실성을 제어하기 위해 **Pydantic** 기반의 검증 레이어를 포함하고 있습니다.

- **날짜 검증:** `start_date`, `end_date` 필드는 반드시 유효한 `YYYY-MM-DD` 형식이어야 합니다.
- **필수 필드 체크:** `sido`, `venue`, `gather_name` 등 주요 비즈니스 로직 정보 누락 시 저장을 중단하고 에러 로그를 남깁니다.
- **스키마 강제:** LLM에게 모델의 JSON Schema를 프롬프트로 제공하여 응답 구조의 일관성을 유지합니다.

---

## 📄 라이선스
MIT License
