import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

try:
    print("--- [테스트] 정식 모델명 호출 시도 ---")

    # 404를 유발하던 'gemini-flash-latest' 대신 정식 명칭 사용
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="안녕? 연결 확인 부탁해."
    )

    print("\n응답 결과:")
    print(response.text)

except Exception as e:
    print(f"\n테스트 실패: \n{e}")