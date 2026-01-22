from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from google import genai
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# [수정 포인트 1] CORS 설정을 더 강력하게 적용합니다.
# 모든 도메인(*)에서 오는 POST, OPTIONS 요청을 허용합니다.
CORS(app, resources={r"/*": {"origins": "*"}})

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# [수정 포인트 2] 브라우저의 OPTIONS 요청(Preflight)을 수동으로 처리해줍니다.
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = make_response()
        res.headers.add("Access-Control-Allow-Origin", "*")
        res.headers.add("Access-Control-Allow-Headers", "Content-Type")
        res.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return res

@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS AI Server is Running"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        system_instruction = """
        너는 '(주)루트랩스(ROOTLABS)'의 공식 전문 AI 비서야... (기존 지침 유지)
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=user_message,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.7,
                "top_p": 0.95
            }
        )

        ai_response = response.text if response.text else "응답 내용이 없습니다."
        return jsonify({"reply": ai_response})

    except Exception as e:
        return jsonify({"reply": f"서버 오류: {str(e)}"}), 500

if __name__ == '__main__':
    # Render 환경의 포트를 명확히 잡습니다.
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
