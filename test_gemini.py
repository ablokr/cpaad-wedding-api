import os
from google import genai
from dotenv import load_dotenv

def test_gemini():
    # .env.local 로드
    load_dotenv(".env.local")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[!] GEMINI_API_KEY가 없습니다.")
        return

    # 모델명 설정 (성공했던 gemini-2.5-flash-lite 권장)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    print(f"[*] 테스트 모델: {model_name}")

    try:
        client = genai.Client(api_key=api_key)

        # 1. 사용 가능한 모델 목록 출력 (디버깅용)
        print("[*] 사용 가능한 모델 목록:")
        for m in client.models.list():
            # generateContent가 가능한 모델만 필터링
            if "generateContent" in m.supported_actions:
                print(f" - {m.name}")

        print("-" * 40)
        
        # 2. 질문 요청
        print(f"[*] '{model_name}' 모델에 질문 전송 중...")
        response = client.models.generate_content(
            model=model_name,
            contents="대한민국의 현재 대통령은 누구야?"
        )
        
        print("\n[✔] 정상 응답 받음!")
        print("=" * 40)
        print(response.text.strip())
        print("=" * 40)
        
    except Exception as e:
        print("\n[✘] 에러 발생:")
        print(e)

if __name__ == "__main__":
    test_gemini()