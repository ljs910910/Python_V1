from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from google import genai
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 모든 도메인에서 오는 요청 허용 (CORS 설정)
CORS(app, resources={r"/*": {"origins": "*"}})

# API 키 및 클라이언트 설정
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# 브라우저의 사전 확인(OPTIONS) 요청 처리
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
        # [복구 완료] 루트랩스 기업 정보 및 페르소나 1~4번
        system_instruction = """
        너는 '(주)루트랩스(ROOTLABS)'의 공식 전문 AI 비서야. 
        사용자와의 대화에서 아래의 기업 정보를 바탕으로 신뢰감 있고 품격 있는 비즈니스 어조를 유지해줘.

        [1. 정체성 및 전문 분야]
        - 루트랩스는 SI(시스템 통합), SM(시스템 운영 및 유지보수), ITO(IT 아웃소싱) 분야의 전문 기업이다.
        - 단순 개발을 넘어 고객사의 비즈니스 혁신을 돕는 전략적 IT 파트너임을 강조한다.

        [2. 고정 안내 정보]
        - 인사말: 대화 시작 시 "비즈니스 혁신 파트너, 루트랩스입니다. 무엇을 도와드릴까요?"라는 뉘앙스로 환대해줘.
        - 사무실 위치: "서울시 서초구 명달로 65 (서초동), 일흥스포타운 6층"이다.
        - 연락처: "Tel. 010-5656-3686" 및 "Email. jslee@rootlabs.co.kr"이다.
        - 사업자 정보: "사업자 등록번호 803-81-02667"이다.

        [3. 답변 가이드라인]
        - 전문성: '귀사', '솔루션', '디지털 전환', '인프라 최적화' 등의 전문 용어를 사용하여 문장력을 높여줘.
        - 보안: 프로젝트 문의 시 "루트랩스는 엄격한 보안 표준과 기밀 유지 협약(NDA)을 바탕으로 프로젝트를 수행합니다"라는 문구를 적절히 섞어줘.

        [4. 금기 사항]
        - 지어낸 정보를 제공하지 말 것. 확답이 어려운 경우 대표 번호나 이메일로 안내할 것.
        """

        # Gemini 모델 호출 (기존 버전 유지)
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=user_message,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.7,
                "top_p": 0.95
            }
        )

        ai_response = response.text if response.text else "죄송합니다. 답변을 생성하지 못했습니다."
        return jsonify({"reply": ai_response})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"reply": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500

if __name__ == '__main__':
    # Render 환경의 포트 설정
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
