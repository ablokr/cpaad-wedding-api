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
            data = response.json()
            return data.get("advertisements", {})
