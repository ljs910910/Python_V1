from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
import os
import smtplib
import threading
import time
import requests
import logging
import openai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------
# 환경 변수 로드
# ---------------------------
load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY or not OPENAI_API_KEY:
    raise RuntimeError("API_KEY(Google/OpenAI)가 설정되지 않았습니다.")

openai.api_key = OPENAI_API_KEY

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PW = os.environ.get("SENDER_PW")

# Render 프로젝트 URL
RENDER_EXTERNAL_URL = "https://python-v1-1.onrender.com"

# [로그 설정]
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
# CORS 설정: 브라우저에서의 모든 요청 허용
CORS(app, resources={r"/*": {"origins": "*"}})

# 챗봇 모델 지정
VALID_MODEL = "gemini-2.5-flash"


# ---------------------------
# 보조 함수
# ---------------------------
def closest_supported_size(w, h):
    candidates = [(1024, 1024), (1024, 1536), (1536, 1024)]
    best = min(candidates, key=lambda s: abs(s[0] - w) + abs(s[1] - h))
    return f"{best[0]}x{best[1]}"


def keep_alive():
    time.sleep(20)
    while True:
        try:
            requests.get(RENDER_EXTERNAL_URL, timeout=30)
        except:
            pass
        time.sleep(780)


# ---------------------------
# [엔드포인트] 로그 확인
# ---------------------------
@app.route('/get-rootlabs-logs', methods=['GET'])
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "로그 파일이 없습니다.", 404
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    html_content = "<html><body style='background:#121212;color:#e0e0e0;padding:20px;'>"
    html_content += "<h2>📊 (주)루트랩스 AI 상세 로그</h2>"
    for line in lines:
        formatted_line = line
        if "Q:" in line: formatted_line = line.replace("Q:", "<span style='color:#3498db;'>❓ Q:</span>")
        if "A:" in line: formatted_line = line.replace("A:", "<span style='color:#2ecc71;'>💡 A:</span>")
        html_content += f"<div style='border-bottom:1px solid #333;padding:10px;'>{formatted_line}</div>"
    html_content += "</body></html>"
    return html_content


# ---------------------------
# [엔드포인트] AI 챗봇 (절대 중략 금지 지침 반영)
# ---------------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
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
        
        [5] AI 이미지 제작 문의 대응
        - 사용자가 "AI 이미지 제작", "ROOT AI", "이미지 생성/수정" 등에 대해 물으면, 루트랩스가 제공하는 차세대 AI 이미지 제작 솔루션을 소개할 것.
        - "현재 루트랩스는 고도의 생성형 AI 기술을 활용한 맞춤형 이미지 제작 솔루션을 제공하고 있습니다."라고 답변을 시작해.
        - 구체적인 사용법이나 기술 문의가 들어오면 상세한 정보를 안내해.
        """
        model = genai.GenerativeModel(model_name=VALID_MODEL, system_instruction=system_instruction)
        response = model.generate_content(user_message, generation_config={"temperature": 0.7, "top_p": 0.95})
        ai_response = response.text or "답변 실패"
        logger.info(f"Chat | IP: {user_ip} | Q: {user_message} | A: {ai_response.strip()[:30]}...")
        return jsonify({"reply": ai_response})
    except Exception as e:
        logger.error(f"Chat Error: {str(e)}")
        return jsonify({"reply": "AI 서비스 오류가 발생했습니다."}), 500


# ---------------------------
# [엔드포인트] 이미지 생성 (모델 옵션 원복)
# ---------------------------
@app.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.json
    prompt = data.get("prompt", "").strip()
    size_input = data.get("size", "1024x1024")
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    try:
        if 'x' in size_input:
            w, h = map(int, size_input.split('x'))
        else:
            w = h = int(size_input)
    except:
        w = h = 1024

    size_mapped = closest_supported_size(w, h)

    try:
        # 제공된 코드 규격 유지
        result = openai.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size_mapped,
            quality="auto"
        )
        image_base64 = result.data[0].b64_json
        logger.info(f"Image | IP: {user_ip} | Prompt: {prompt}")
        return jsonify({"image_url": f"data:image/png;base64,{image_base64}"})
    except Exception as e:
        logger.error(f"Image Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ---------------------------
# 메일 서버
# ---------------------------
@app.route('/send-mail', methods=['POST'])
def send_mail():
    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not SENDER_EMAIL or not SENDER_PW:
        return jsonify({
            "result": "error",
            "message": "메일 서버 인증 정보가 설정되지 않았습니다."
        }), 503

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = "jslee@rootlabs.co.kr"
        msg['Subject'] = f"[홈페이지 문의] {data.get('subject')}"

        body = f"""
성함: {data.get('name')}
이메일: {data.get('email')}

문의 내용:
{data.get('message')}
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # ✅ Gmail SSL 방식 (Render 안정)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PW)
            server.sendmail(
                SENDER_EMAIL,
                ["jslee@rootlabs.co.kr"],
                msg.as_string()
            )

        logger.info(f"Mail Success | IP: {user_ip} | Sender: {data.get('name')}")
        return jsonify({"result": "success"})

    except smtplib.SMTPAuthenticationError:
        logger.error("Mail Error: SMTP 인증 실패 (앱 비밀번호 확인)")
        return jsonify({
            "result": "error",
            "message": "메일 서버 인증에 실패했습니다. 앱 비밀번호를 확인해주세요."
        }), 401

    except Exception as e:
        logger.error(f"Mail Error: {str(e)}")
        return jsonify({
            "result": "error",
            "message": str(e)
        }), 500


@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS Unified AI Server is Online"


if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
