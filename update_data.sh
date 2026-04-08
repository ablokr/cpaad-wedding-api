#!/bin/bash
set -e

# ==========================================
# Wedding CPA 데이터 자동 업데이트 스크립트 (Main 브랜치 직접 커밋)
# ==========================================

# 1. 깃허브 토큰($GITHUB_TOKEN) 로드
if [ -z "$GITHUB_TOKEN" ]; then
    ENV_FILE=".env.local"
    if [ -f "$ENV_FILE" ]; then
        FILE_TOKEN=$(grep '^GITHUB_TOKEN=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"'\'' ')
        if [ -n "$FILE_TOKEN" ]; then
            export GITHUB_TOKEN="$FILE_TOKEN"
            echo "[*] GITHUB_TOKEN을 $ENV_FILE 에서 로드했습니다."
        fi
    fi
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "[✘] GITHUB_TOKEN 환경 변수가 설정되어 있지 않습니다."
    exit 1
fi

# 2. 실행 로그를 위한 타임스탬프
echo "===== 작업 시작: $(date '+%Y-%m-%d %H:%M:%S') ====="

# [필수] Git 사용자 정보 설정 체크 (없으면 기본값 또는 환경변수 사용)
if [ -z "$(git config user.name)" ]; then
    echo "[*] Git 사용자 정보가 없어 설정을 진행합니다."
    # 환경변수에서 가져오되, 없으면 기본 봇 정보 사용 (보안 유지)
    GIT_NAME="${GIT_USER_NAME:-ablo-bot}"
    GIT_EMAIL="${GIT_USER_EMAIL:-bot@ablo.dot.kr}"
    
    git config --local user.name "$GIT_NAME"
    git config --local user.email "$GIT_EMAIL"
fi

# 3. 메인 소스 코드 최신화
echo "[*] 소스 코드 최신 버전 가져오는 중 (main)..."
# 실행 권한 변경 등으로 인한 미세 충돌 무시를 위해 강제 전환
git checkout -f main
git pull origin main

# 4. 분석 파이프라인 실행
echo "[*] 데이터 수집 및 AI 분석 파이프라인 실행 중..."
python3 src/main.py

# 5. 데이터 커밋 및 푸시 (Main 브랜치 직접 반영)
echo "[*] 생성된 최신 데이터를 메인 저장소(main)에 반영 중..."
git add -f data/

# 스테이징된 파일 수 및 Ahead 커밋 수 확인
STAGED_COUNT=$(git status --porcelain | grep '^[AM]' | wc -l)
AHEAD_COUNT=$(git rev-list --count origin/main..main 2>/dev/null || echo "0")
echo "[*] 스테이징된 파일: $STAGED_COUNT, 미전송 커밋(Ahead): $AHEAD_COUNT"

# 신규 파일이 있거나, 이미 커밋은 되었지만 푸시되지 않은(Ahead) 상태일 때 푸시 시도
if [ "$STAGED_COUNT" -gt 0 ] || [ "$AHEAD_COUNT" -gt 0 ]; then
    if [ "$STAGED_COUNT" -gt 0 ]; then
        COMMIT_MSG="chore: $(date '+%Y-%m-%d %H:%M:%S') 데이터 자동 업데이트"
        git commit -m "$COMMIT_MSG"
    fi
    
    # 원격 저장소 주소 추출
    REMOTE_URL=$(git config --get remote.origin.url)
    REPO_PATH=$(echo "$REMOTE_URL" | sed -E 's/.*github.com[:\/]//; s/\.git$//')
    PUSH_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO_PATH}.git"
    
    echo "[*] 최신 데이터를 원격 저장소($REPO_PATH)로 전송 중..."
    if git push "$PUSH_URL" main; then
        echo "[✔] 데이터 동기화 성공! 모든 커밋이 'main'에 반영되었습니다."
    else
        echo "[✘] 푸시 실패. 권한이나 네트워크 상태를 확인하세요."
    fi
else
    echo "[*] 변경된 캠페인이나 데이터가 없어 작업을 종료합니다."
fi

echo "===== 작업 완료: $(date '+%Y-%m-%d %H:%M:%S') ====="
