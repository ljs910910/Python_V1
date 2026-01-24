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

# [로그 설정] 간소화된 포맷: 시간과 메시지만 기록
LOG_FILE = "chat_history.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
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
# 모델 지정 (2.5-flash-lite 유지)
# ---------------------------
VALID_MODEL = "gemini-2.5-flash-lite"


# ---------------------------
# 서버 슬립 방지 (Self-Ping) 로직
# ---------------------------
def keep_alive():
    time.sleep(20)
    while True:
        try:
            requests.get(RENDER_EXTERNAL_URL, timeout=30)
        except Exception:
            pass
        time.sleep(300)


# ---------------------------
# [가독성 강화] 로그 확인용 엔드포인트
# ---------------------------
@app.route('/get-rootlabs-logs', methods=['GET'])
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "로그 파일이 아직 생성되지 않았습니다.", 404

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>ROOTLABS Chat Logs</title>
        <style>
            body { background-color: #121212; color: #e0e0e0; font-family: sans-serif; padding: 20px; line-height: 1.6; }
            .log-entry { border-bottom: 1px solid #333; padding: 12px 0; }
            .ip { color: #00adb5; font-weight: bold; }
            .question { color: #3498db; font-weight: bold; display: block; }
            .answer { color: #2ecc71; display: block; white-space: pre-wrap; margin-top: 5px; }
            .error { color: #ff4b2b; font-weight: bold; }
            .divider { color: #f1c40f; margin: 15px 0; font-weight: bold; }
            h2 { color: #ffffff; border-bottom: 3px solid #00adb5; display: inline-block; padding-bottom: 5px; }
        </style>
    </head>
    <body>
        <h2>📊 (주)루트랩스 AI 대화 상세 로그</h2>
        <div style="margin-top:20px;">
    """

    for line in lines:
        formatted_line = line
        if "Q:" in line:
            formatted_line = line.replace("Q:", "<span class='question'>❓ Q:</span>")
        if "A:" in line:
            formatted_line = line.replace("A:", "<span class='answer'>💡 A:</span>")
        if "Error:" in line:
            formatted_line = line.replace("Error:", "<span class='error'>❌ Error:</span>")
        if "IP:" in line:
            formatted_line = line.replace("IP:", "<span class='ip'>🌐 IP:</span>")
        if "━━━━" in line:
            formatted_line = f"<div class='divider'>{line}</div>"

        html_content += f"<div class='log-entry'>{formatted_line}</div>"

    html_content += "</div></body></html>"
    return html_content


@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS Unified AI & Mail Server is Running"


# ---------------------------
# AI 챗봇 엔드포인트
# ---------------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        # [원복] 1~4번 system_instruction 완벽 복구
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
        ai_response = response.text or "답변 실패"

        # [간소화된 로깅] 불필요한 정보 제거
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"IP: {user_ip}")
        logger.info(f"Q: {user_message}")
        logger.info(f"A: {ai_response.strip()}")

        return jsonify({"reply": ai_response})

    except Exception as e:
        error_str = str(e)
        # [간소화된 에러 로깅] violations, quota_id 등 복잡한 문구 완전 제거
        status = "할당량 초과(429)" if "429" in error_str or "quota" in error_str.lower() else "시스템 에러"

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"IP: {user_ip}")
        logger.info(f"Q: {user_message}")
        logger.info(f"Error: {status}")

        if "429" in error_str or "quota" in error_str.lower():
            return jsonify({"reply": "현재 문의량이 많아 잠시 서비스가 지연되고 있습니다. 잠시 후 다시 시도해주세요."}), 429
        return jsonify({"reply": "AI 서비스 오류가 발생했습니다."}), 500


# ---------------------------
# 이메일 발송 엔드포인트 (기본 유지)
# ---------------------------
@app.route('/send-mail', methods=['POST'])
def send_mail():
    data = request.json
    try:
        if not SENDER_EMAIL or not SENDER_PW: return jsonify({"result": "error"}), 503
        msg = MIMEMultipart()
        msg['From'] = f"ROOTLABS Contact <{SENDER_EMAIL}>"
        msg['To'] = "jslee@rootlabs.co.kr"
        msg['Subject'] = f"[홈페이지 문의] {data.get('subject')}"
        msg.attach(MIMEText(f"성함: {data.get('name')}\n내용: {data.get('message')}", 'plain'))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls();
            server.login(SENDER_EMAIL, SENDER_PW)
            server.sendmail(SENDER_EMAIL, "jslee@rootlabs.co.kr", msg.as_string())
        return jsonify({"result": "success"})
    except:
        return jsonify({"result": "error"}), 500


if __name__ == "__main__":
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
