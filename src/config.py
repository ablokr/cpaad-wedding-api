import os
import json
from typing import Any, Dict
from dotenv import load_dotenv

class AppConfig:
    """
    애플리케이션의 모든 설정을 통합 관리하는 클래스입니다.
    config.json(기본값) -> .env.local(환경변수) 순으로 우선순위를 가집니다.
    """
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # 1. 파일 위치 기준으로 프로젝트 루트 경로 탐색 (src/config.py 기준 한 단계 위)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 2. .env.local 로드 (절대 경로 사용으로 실행 위치와 무관하게 동작 보장)
        env_path = os.path.join(root_dir, ".env.local")
        load_dotenv(env_path)

        # 3. config.json 로드
        config_path = os.path.join(root_dir, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            # 기본값 (파일이 없을 경우)
            self._config = {
                "api": {"url": "https://cpaad.co.kr/api/ad_json_date.php", "timeout": 30.0},
                "ai": {"model": "gemini-3.1-flash-lite-preview"},
                "pipeline": {"max_workers": 6, "max_retries": 3}
            }

    @property
    def api_url(self) -> str:
        return self._config.get("api", {}).get("url", "https://cpaad.co.kr/api/ad_json_date.php")

    @property
    def ai_model(self) -> str:
        return os.getenv("GEMINI_MODEL", self._config.get("ai", {}).get("model", "gemini-3.1-flash-lite-preview"))

    @property
    def max_workers(self) -> int:
        return self._config.get("pipeline", {}).get("max_workers", 3)

    @property
    def max_retries(self) -> int:
        return self._config.get("pipeline", {}).get("max_retries", 3)

    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def google_api_key(self) -> str:
        # DATA_DIR 기반 데이터셋별 전용 키 우선 조회
        # 예: DATA_DIR=data/weddingExpo → GEMINI_API_KEY_WEDDINGEXPO
        data_dir = os.getenv("DATA_DIR", "")
        if data_dir:
            # data/weddingExpo → WEDDINGEXPO
            dataset_name = os.path.basename(data_dir).upper()
            dataset_key = os.getenv(f"GEMINI_API_KEY_{dataset_name}")
            if dataset_key:
                return dataset_key
        # 폴백: 공통 키 (GOOGLE_API_KEY 또는 GEMINI_API_KEY)
        return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """기타 설정값 조회"""
        return self._config.get(section, {}).get(key, default)

# 싱글톤 인스턴스 제공
config = AppConfig()
