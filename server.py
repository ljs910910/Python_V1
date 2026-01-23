from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
import os
import smtplib
import threading
import time
import requests
import logging
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

# Render 프로젝트의 실제 URL
RENDER_EXTERNAL_URL = "https://python-v1-1.onrender.com"

# [로그 설정]
LOG_FILE = "chat_history.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Google AI client 설정
genai.configure(api_key=API_KEY)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------------------------
# 모델 지정
# ---------------------------
VALID_MODEL = "gemini-2.5-flash-lite"


# ---------------------------
# [신규] 서버 슬립 방지 (Self-Ping) 로직
# ---------------------------
def keep_alive():
    time.sleep(20)
    logger.info(f"🚀 Self-Ping 스레드가 활성화되었습니다. 대상: {RENDER_EXTERNAL_URL}")
    while True:
        try:
            response = requests.get(RENDER_EXTERNAL_URL, timeout=30)
            print(f"Self-Ping Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Self-Ping Error: {e}")
        time.sleep(300)


# ---------------------------
# [신규] 로그 확인용 엔드포인트 (무료티어 Shell 대용)
# ---------------------------
@app.route('/get-rootlabs-logs', methods=['GET'])
def view_logs():
    """브라우저에서 로그 파일을 텍스트로 확인하는 경로"""
    if not os.path.exists(LOG_FILE):
        return "로그 파일이 아직 생성되지 않았습니다.", 404

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()

    return Response(log_content, mimetype='text/plain')


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

    # 접속자 IP 파악
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        # [유지] 기존 system_instruction 가이드라인 및 정보 보존
        system_instruction = """
        너는 '(주)루트랩스(ROOTLABS)'의 공식 전문 AI 비서야.

        [1] 정체성 및 전문 분야
        - 루트랩스는 SI, SM, ITO 분야의 전문 기업 (디지털 전환 중심)

        [2] 응대 원칙 (인삿말 최적화)
        - 사용자가 "안녕하세요", "하이", "Hi", "안녕" 등 단순 인사를 할 경우, 매번 똑같은 고정 안내 문구(비즈니스 혁신 파트너...)를 반복하지 마.
        - 인사에는 "안녕하세요! (주)루트랩스 AI 비서입니다. 어떤 프로젝트나 기술 지원에 대해 도움을 드릴까요?"와 같이 자연스럽게 대화를 시작해.
        - 이후 구체적인 질문이 들어오면 그때 루트랩스의 전문 정보를 상세히 제공해.

        [3] 고정 정보 (필요시 제공)
        - 위치: 서울시 서초구 명달로 65, 일흥스포타운 6층
        - 연락처: Tel. 010-5656-3686 / Email. jslee@rootlabs.co.kr
        - 사업자 등록번호: 803-81-02667

        [4] 답변 스타일
        - 전문 용어 & 비즈니스 어조 유지
        - 지어낸 정보 제공 금지 및 보안 준수
        """

        model = genai.GenerativeModel(model_name=VALID_MODEL, system_instruction=system_instruction)
        response = model.generate_content(
            user_message,
            generation_config={"temperature": 0.7, "top_p": 0.95}
        )
        ai_response = response.text or "답변 생성 실패"

        # [로그 기록]
        logger.info(f"CHAT_LOG | IP: {user_ip} | User: {user_message} | AI: {ai_response[:50]}...")

        return jsonify({"reply": ai_response})

    except Exception as e:
        logger.error(f"AI 에러 발생 (IP: {user_ip}): {e}")
        if "quota" in str(e).lower() or "429" in str(e):
            return jsonify({"reply": "챗봇 무료 할당량 초과! 잠시 후 다시 시도해주세요."}), 429
        return jsonify({"reply": "AI 서비스 오류"}), 500


# ---------------------------
# 이메일 발송 엔드포인트
# ---------------------------
@app.route('/send-mail', methods=['POST'])
def send_mail():
    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        if not SENDER_EMAIL or not SENDER_PW:
            return jsonify({"result": "error", "message": "메일 발송 설정이 없습니다."}), 503

        msg = MIMEMultipart()
        msg['From'] = f"ROOTLABS Contact <{SENDER_EMAIL}>"
        msg['To'] = "jslee@rootlabs.co.kr"
        msg['Subject'] = f"[홈페이지 문의] {data.get('subject')}"

        html_body = f"""
        <div style='padding:20px;font-family:sans-serif;'>
            <h2>신규 프로젝트 문의 (접속IP: {user_ip})</h2>
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

        logger.info(f"MAIL_LOG | IP: {user_ip} | From: {data.get('email')} | Success")
        return jsonify({"result": "success"})
    except Exception as e:
        logger.error(f"Mail Error (IP: {user_ip}): {e}")
        return jsonify({"result": "error", "message": str(e)}), 500


# ---------------------------
# 서버 시작
# ---------------------------
if __name__ == "__main__":
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
