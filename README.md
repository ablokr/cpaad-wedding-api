# Wedding CPA Data Pipeline 👰🤵

CPAAD 웨딩 박람회 캠페인 데이터를 자동으로 **수집 → AI 분석 → 구조화 → 저장**하는 파이프라인입니다. Playwright 웹 캡처와 Gemini Vision API를 결합해 캠페인 페이지를 분석하고, 증분 업데이트(Incremental Update) 방식으로 변경된 캠페인만 효율적으로 처리합니다.

---

## 📁 프로젝트 구조

```
cpaad-wedding-api/
├── src/
│   ├── main.py          # 파이프라인 총괄 실행 엔트리포인트
│   ├── config.py        # 설정 통합 관리 (싱글톤)
│   ├── api_loader.py    # 외부 API 원본 데이터 로드
│   ├── collector.py     # Playwright 모바일 웹 캡처
│   ├── preprocessor.py  # 원본 데이터 전처리 (주소 파싱 등)
│   ├── processor.py     # Gemini Vision AI 분석 + Pydantic 검증
│   └── storage.py       # JSON 입출력, 증분 업데이트, 지역 매핑
├── lib/
│   └── regionMapping.json  # 시도/시군구 한→영 매핑 테이블
├── data/
│   ├── captures/           # 캡처 이미지 (공유, 데이터셋 무관)
│   └── weddinggo/          # 데이터셋별 디렉토리 (아래 상세 설명)
├── config.json          # AI 모델, 파이프라인, API 기본 설정
├── .env.local           # 시크릿 키 및 환경 변수 (git 제외)
└── update_data.sh       # 자동화 실행 스크립트
```

---

## ⚙️ 설정 파일 상세

### 1. `.env.local` — 시크릿 키 및 환경 변수

프로젝트 루트에 `.env.local` 파일을 생성하세요. **이 파일은 절대 git에 커밋하지 마세요.**

```env
# ─────────────────────────────────────────
# [필수] Google Gemini API 키
# https://aistudio.google.com/app/apikey 에서 발급
# ─────────────────────────────────────────
GEMINI_API_KEY=AIza...your_key_here

# GOOGLE_API_KEY도 동일하게 인식됩니다 (둘 중 하나만 설정)
# GOOGLE_API_KEY=AIza...your_key_here

# ─────────────────────────────────────────
# [필수] GitHub Personal Access Token (PAT)
# 권한: Contents → Read & Write
# https://github.com/settings/tokens 에서 발급
# ─────────────────────────────────────────
GITHUB_TOKEN=github_pat_...your_token_here

# ─────────────────────────────────────────
# [선택] Git 커밋 작성자 정보
# 미설정 시 기본값: ablo-bot / bot@ablo.dot.kr
# ─────────────────────────────────────────
GIT_USER_NAME="ablo-bot"
GIT_USER_EMAIL="bot@example.com"

# ─────────────────────────────────────────
# [선택] AI 모델 오버라이드
# config.json의 ai.model 보다 우선 적용됩니다
# ─────────────────────────────────────────
# GEMINI_MODEL=gemini-2.0-flash

# ─────────────────────────────────────────
# [선택] 데이터 경로 오버라이드 (멀티 데이터셋 시 활용)
# 미설정 시 기본값: data/weddinggo / data/captures
# ─────────────────────────────────────────
# DATA_DIR=data/weddinggo
# CAPTURE_DIR=data/captures
```

> **우선순위**: `.env.local` 환경변수 > `config.json` 기본값

---

### 2. `config.json` — 파이프라인 동작 설정

코드 변경 없이 동작을 조정할 수 있는 설정 파일입니다.

```json
{
  "api": {
    "url": "https://cpaad.co.kr/api/ad_json_date.php",
    "timeout": 30.0
  },
  "ai": {
    "_comment": "모델명은 임의 변경 금지! 비즈니스 로직에 최적화된 값입니다.",
    "model": "gemini-3.1-flash-lite-preview"
  },
  "pipeline": {
    "max_workers": 6,       // 동시 처리 캠페인 수
    "max_retries": 3,       // 실패 시 최대 재시도 횟수
    "retry_delay_seconds": 2 // 재시도 간격(초, 지수 증가)
  }
}
```

| 키 | 설명 | 기본값 |
|---|---|---|
| `api.timeout` | API 요청 타임아웃(초) | `30.0` |
| `ai.model` | Gemini 모델명 | `gemini-3.1-flash-lite-preview` |
| `pipeline.max_workers` | 병렬 처리 수 (높을수록 빠르나 API 부하 증가) | `6` |
| `pipeline.max_retries` | 503 등 일시 오류 시 재시도 횟수 | `3` |
| `pipeline.retry_delay_seconds` | 1차 재시도 대기(초). 이후 지수 증가 | `2` |

---

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

> **ARM 아키텍처(M1/M2 Mac, Raspberry Pi 등)**: Chromium 설치 실패 시 Firefox로 자동 폴백됩니다.

### 2. 단독 실행

```bash
python3 src/main.py
```

### 3. 자동화 스크립트 (권장)

`update_data.sh`는 소스 최신화 → 파이프라인 실행 → 결과 커밋/푸시를 한 번에 처리합니다.

```bash
chmod +x update_data.sh
./update_data.sh
# 또는 source로 실행 (현재 셸 환경 유지)
. update_data.sh
```

### 4. Cron 자동화 (6시간 간격)

```bash
crontab -e
```

```cron
0 */6 * * * /절대경로/update_data.sh >> /절대경로/cron_log.log 2>&1
```

---

## 🧩 파이프라인 동작 원리

```
[API 로드] → [종료 캠페인 정리] → [변경 감지] → [캡처] → [AI 분석] → [저장] → [캐시 갱신]
```

### 증분 업데이트 (Incremental Update) 로직

매번 전체를 재수집하지 않고, 변경된 캠페인만 처리합니다.

| 조건 | 처리 |
|---|---|
| 캠페인 파일 없음 | → 신규 수집 대상 |
| 파일 있음 + 캐시와 API 데이터 **다름** | → 변경 수집 대상 |
| 파일 있음 + 캐시와 API 데이터 **동일** | → **스킵** (중복 방지) |
| API 응답에 없는 캐시 캠페인 | → 종료 감지 → 파일 및 색인 삭제 |

> **캐시(`api_cache.json`)는 성공한 캠페인만 갱신됩니다.**  
> 503 등으로 실패한 캠페인은 캐시가 갱신되지 않아, 다음 실행 시 자동으로 재처리 대상에 포함됩니다.

---

## 📦 멀티 데이터셋 지원

환경 변수로 데이터 경로를 동적으로 지정하면, **단일 소스 코드로 여러 데이터셋**을 독립적으로 관리할 수 있습니다.

### 구조 예시

```
data/
├── captures/          # 캡처 이미지 (모든 데이터셋 공유)
├── weddinggo/         # 데이터셋 A
│   ├── api_cache.json
│   ├── all.json
│   ├── all_index.json
│   ├── campaigns/
│   ├── regions/
│   └── cpaad/
└── honeymoon/         # 데이터셋 B (미래 확장)
    ├── api_cache.json
    └── ...
```

### 실행 방법

```bash
# 기본 (weddinggo)
python3 src/main.py

# 다른 데이터셋 지정
DATA_DIR=data/honeymoon python3 src/main.py

# 캡처 경로도 별도 지정
DATA_DIR=data/honeymoon CAPTURE_DIR=data/captures python3 src/main.py
```

### `update_data.sh`에서 데이터셋 지정

```bash
# .env.local에 추가하거나 스크립트 호출 시 인라인으로 지정
DATA_DIR=data/honeymoon . update_data.sh
```


data/weddingExpo 에 데이터를 저장하면서 파이프라인을 실행하려면 터미널에서 아래와 같이 실행하시면 됩니다.

방법 1: 직접 실행 (테스트 용도)

bash
DATA_DIR=data/weddingExpo python3 src/main.py
방법 2: 전체 자동화 스크립트로 실행 (커밋 & 푸시까지)

bash
DATA_DIR=data/weddingExpo . update_data.sh
이렇게 하면 config.py와 processor.py에서 DATA_DIR 환경 변수를 읽어 다음과 같이 동작합니다:

GEMINI_API_KEY_WEDDINGEXPO 로 설정한 API 키를 우선적으로 사용합니다. (없을 경우 기본키 사용)
processor.py에 작성한 20대/30대 경어체 커뮤니티 페르소나(weddingExpo)를 자동으로 적용하여 AI 콘텐츠를 생성합니다.
생성된 데이터 결과물(all.json, campaigns/, regions/ 등)을 data/weddingExpo/ 경로 내에 저장합니다.

---

## 🤖 Gemini API 설정

### API 키 발급

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **Create API key** 클릭
3. 발급된 키를 `.env.local`의 `GEMINI_API_KEY`에 설정

### 모델 변경

`.env.local`에서 오버라이드 (권장):
```env
GEMINI_MODEL=gemini-2.0-flash
```

또는 `config.json`에서 변경:
```json
{
  "ai": {
    "model": "gemini-2.0-flash"
  }
}
```

> ⚠️ 모델 변경 시 프롬프트 응답 형식이 달라져 Pydantic 검증이 실패할 수 있습니다. 기본값(`gemini-3.1-flash-lite-preview`) 사용을 권장합니다.

### 503 오류 대응 (고부하)

Gemini API가 일시적으로 503을 반환할 경우, 파이프라인은 `max_retries`만큼 지수 백오프 재시도를 수행합니다. 모든 재시도가 실패해도 해당 캠페인의 **캐시는 갱신되지 않아**, 다음 실행에서 자동 재처리됩니다.

```
1차 실패 → 2초 대기 → 2차 실패 → 4초 대기 → 3차 실패 → 6초 대기 → 최종 실패 (스킵)
                                                                       ↓
                                                          캐시 미갱신 → 다음 실행에서 재시도
```

---

## 📊 산출물 구조 (`data/<dataset>/`)

| 파일/폴더 | 설명 |
|---|---|
| `api_cache.json` | API 원본 스냅샷. 증분 업데이트 비교 기준. 성공 캠페인만 갱신. |
| `campaigns/<id>.json` | 개별 캠페인 AI 분석 상세 데이터 |
| `all.json` | 전체 캠페인 상세 데이터 + 통계 (`stats`) |
| `all_index.json` | 전체 캠페인 요약 색인 + 통계 (`stats`) |
| `regions/<region>.json` | 지역별 캠페인 상세 목록 |
| `regions/<region>_index.json` | 지역별 캠페인 요약 색인 |
| `cpaad/ad_json_date.json` | API 원본 응답 백업 |
| `data/captures/<id>_capture.png` | 캠페인 페이지 모바일 캡처 이미지 |

### `all.json` 응답 구조 예시

```json
{
  "stats": {
    "total_count": 151,
    "region_count": 9,
    "district_count": 47,
    "updated_at": "2026-04-15 15:31:47"
  },
  "items": [
    {
      "campaign_id": "planon60",
      "gather_name": "용산 웨딩박람회",
      "region_en": "seoul",
      ...
    }
  ]
}
```

---

## 🔄 GitHub Actions 연동

`data/weddinggo/all.json`이 `api-data` 브랜치에 푸시될 때 외부 저장소(`ablokr/wedding-html`)의 빌드를 자동으로 트리거합니다.

```
[update_data.sh] → [GitHub: api-data 브랜치 푸시]
                          ↓
              [trigger-build-weddinggo-html.yml]
                          ↓
              [ablokr/wedding-html] 빌드 트리거
```

**필요 Secret**: `Settings → Secrets → WEDDINGGO_PAT_TOKEN`
- 권한: `ablokr/wedding-html` 저장소의 `repo` 또는 `workflow` 권한 PAT

---

## 🛡️ 보안 주의사항

- `.env.local`은 **절대 git에 커밋하지 마세요** (`.gitignore`에 등록됨)
- `GITHUB_TOKEN`은 최소 권한(해당 레포 `Contents: Write` 전용)으로 발급하세요
- `GEMINI_API_KEY`는 Google Cloud Console에서 API 제한(HTTP referrer 또는 IP) 설정을 권장합니다

---

## 🐛 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `JSONDecodeError: Expecting value` | `api_cache.json`이 비어있거나 손상됨 | 자동 복구됨. 빈 `{}` 로 초기화 후 전체 재수집 |
| `503 UNAVAILABLE` | Gemini API 일시 과부하 | 자동 재시도. 실패 시 다음 실행에서 재처리 |
| `Firefox 실행 실패 → Chromium 폴백` | ARM 환경에서 Firefox 미지원 | 정상 동작. Chromium으로 자동 전환 |
| 캠페인이 계속 스킵됨 | 이전 실패가 캐시에 기록되었을 가능성 | 해당 캠페인 JSON 파일 삭제 후 재실행 |
| `GITHUB_TOKEN 환경 변수가 설정되어 있지 않습니다` | `.env.local` 누락 또는 토큰 미설정 | `.env.local` 파일 생성 및 토큰 입력 |
