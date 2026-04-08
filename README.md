# Wedding CPA Data Pipeline 👰🤵

이 프로젝트는 웨딩 박람회 및 CPA 캠페인 데이터를 자동으로 수집, 분석, 구조화하여 저장하는 AI 기반의 데이터 파이프라인입니다.

---

## 🏗️ 프로젝트 구조 (모듈형)

가독성과 유지보수성을 극대화하기 위해 역할을 영역별로 분리하였습니다.

- **`src/main.py`**: 전체 파이프라인 지휘 및 실행 엔트리포인트.
- **`src/api_loader.py`**: 외부 API로부터 원본 데이터를 로드.
- **`src/collector.py`**: Playwright를 이용한 웹 캡처(모바일 뷰).
- **`src/processor.py`**: Gemini AI 연동 시각 분석 및 Pydantic 데이터 검증.
- **`src/storage.py`**: 데이터 입출력, 증분 업데이트(Incremental Update), 지역 매핑.

---

## 🛠️ 설치 및 설정

### 1. 환경 변수 준비
`.env.local` 또는 `.env` 파일을 프로젝트 루트에 생성하고 다음 항목을 설정합니다.
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. 의존성 설치
```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 🚀 실행 및 자동화 (리눅스 서버 권장)

### 1. GitHub 토큰(PAT) 보안 설정
로컬 서버에서 안전하게 푸시하기 위해 서버의 환경 변수에 토큰을 등록합니다.

1. 터미널에서 `nano ~/.bashrc` 실행.
2. 가장 하단에 아래 내용 추가:
   ```bash
   export GITHUB_TOKEN="생성된_토큰_값"
   ```
3. 저장 후 `source ~/.bashrc` 실행.
   - 이렇게 하면 `update_data.sh` 스크립트 내에서 `$GITHUB_TOKEN` 변수를 활용해 인증 주소를 유동적으로 구성할 수 있습니다.

### 2. 자동화 스크립트 실행 (update_data.sh)
제공된 쉘 스크립트는 `main` 로직을 실행한 후 결과물(`data/`)만 `api-data` 브랜치에 안전하게 푸시합니다.
```bash
chmod +x update_data.sh
./update_data.sh
```

### 3. Crontab 등록
6시간마다 자동으로 데이터를 갱신하도록 설정합니다.
```bash
# crontab -e 실행 후 추가
0 */6 * * * /절대경로/update_data.sh
```

---

## 📊 산출물 구조 (`data/`)
- `campaigns/`: 개별 캠페인 상세 JSON 데이터.
- `regions/`: 지역별(서울, 경기 등) 집계 및 색인 파일.
- `captures/`: 분석 전용 스크린샷 이미지.
- `all_index.json`: 전체 캠페인 요약 리스트.
