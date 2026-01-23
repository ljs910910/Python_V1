from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------
# 환경 변수 로드
# ---------------------------
load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY가 설정되지 않았습니다.")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PW = os.environ.get("SENDER_PW")

# Google AI client 설정
genai.configure(api_key=API_KEY)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------------------------
# 모델 지정
# ---------------------------
VALID_MODEL = "gemini-2.5-flash-lite"  # Free Tier에서 가장 많은 호출 가능

# ---------------------------
# 루트 테스트
# ---------------------------
@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS Unified AI & Mail Server is Running"

# ---------------------------
# AI 챗봇 엔드포인트
# ---------------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        system_instruction = """
        너는 '(주)루트랩스(ROOTLABS)'의 공식 전문 AI 비서야.

        [1] 정체성 및 전문 분야
        - 루트랩스는 SI, SM, ITO 분야의 전문 기업
        - 디지털 전환 및 솔루션 중심

        [2] 고정 안내 정보
        - "비즈니스 혁신 파트너, 루트랩스입니다. 무엇을 도와드릴까요?"
        - 위치: 서울시 서초구 명달로 65, 일흥스포타운 6층
        - 연락처: Tel. 010-5656-3686 / Email. jslee@rootlabs.co.kr
        - 사업자 등록번호: 803-81-02667

        [3] 답변 가이드라인
        - 전문 용어 & 비즈니스 어조 유지
        - 보안: NDA 준수 문구 포함

        [4] 금기
        - 지어낸 정보 제공 금지
        """

        # 모델 호출
        model = genai.GenerativeModel(model_name=VALID_MODEL, system_instruction=system_instruction)

        # 텍스트 생성
        response = model.generate_content(
            user_message,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95
            }
        )

        ai_response = response.text or "답변 생성 실패"

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] User: {user_message} | Model {VALID_MODEL} | Reply: {ai_response[:40]}...")

        return jsonify({"reply": ai_response})

    except Exception as e:
        # 429 quota 초과 에러도 catch
        if "quota" in str(e).lower() or "429" in str(e):
            return jsonify({"reply": "무료 할당량 초과! 잠시 후 다시 시도해주세요."}), 429
        print(f"!!! AI 에러: {e}")
        return jsonify({"reply": "AI 서비스 오류"}), 500

# ---------------------------
# 이메일 발송 엔드포인트
# ---------------------------
@app.route('/send-mail', methods=['POST'])
def send_mail():
    data = request.json
    try:
        if not SENDER_EMAIL or not SENDER_PW:
            return jsonify({"result": "error", "message": "메일 발송 설정이 없습니다."}), 503

        msg = MIMEMultipart()
        msg['From'] = f"ROOTLABS Contact <{SENDER_EMAIL}>"
        msg['To'] = "jslee@rootlabs.co.kr"
        msg['Subject'] = f"[홈페이지 문의] {data.get('subject')}"

        html_body = f"""
        <div style='padding:20px;font-family:sans-serif;'>
            <h2>신규 프로젝트 문의</h2>
            <p><b>성함/업체명:</b> {data.get('name')}</p>
            <p><b>Email:</b> {data.get('email')}</p>
            <div style='margin-top:15px;'>
                <p><b>문의 내용:</b></p>
                <p>{data.get('message').replace(chr(10), '<br>')}</p>
            </div>
        </div>
        """
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PW)
            server.sendmail(SENDER_EMAIL, "jslee@rootlabs.co.kr", msg.as_string())

        return jsonify({"result": "success"})

    except Exception as e:
        print(f"!!! Mail Error: {e}")
        return jsonify({"result": "error", "message": str(e)}), 500

# ---------------------------
# 서버 시작
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
