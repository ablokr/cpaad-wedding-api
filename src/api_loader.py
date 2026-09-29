import httpx

from config import config

class WeddingApiLoader:
    @classmethod
    async def fetch_all_ads(cls):
        """
        config에 정의된 외부 API 서버에서 광고 데이터를 실시간으로 가져옵니다.
        """
        api_url = config.api_url
        print(f"[*] [Loader] API 데이터 로딩 중: {api_url}")
        async with httpx.AsyncClient(timeout=config.get("api", "timeout", 30.0)) as http_client:
            response = await http_client.get(api_url)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("advertisements"), dict):
                raise ValueError("API 응답의 advertisements 형식이 올바르지 않습니다")
            if not payload["advertisements"]:
                raise ValueError("API 응답에 캠페인이 없습니다. 기존 데이터 삭제를 막기 위해 중단합니다")
            return payload
