from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from google import genai
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# 로컬 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# 모든 도메인(*)에서의 접속을 허용 (CORS 설정)
CORS(app, resources={r"/*": {"origins": "*"}})

# 전역 클라이언트 변수
_client = None


def get_ai_client():
    """API 키를 안전하게 가져와 클라이언트를 생성합니다."""
    global _client
    api_key = os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        print("!!! ERROR: GOOGLE_API_KEY를 찾을 수 없습니다.")
        return None

    if _client is None:
        try:
            _client = genai.Client(api_key=api_key)
            print("--- Google AI Client 초기화 성공 ---")
        except Exception as e:
            print(f"!!! Client 생성 실패: {e}")
            return None
    return _client


@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS Unified AI & Mail Server is Running"


# --- [기능 1] AI 챗봇 엔드포인트 ---
@app.route('/chat', methods=['POST'])
def chat():
    client = get_ai_client()
    if not client:
        return jsonify({"reply": "서버 설정 오류"}), 500

    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        # [사용자 요청 페르소나 100% 적용]
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

        # 모델명 유지: gemini-flash-latest
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

        # 로그 출력
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] User: {user_message} | AI: {ai_response[:30]}...")

        return jsonify({"reply": ai_response})

    except Exception as e:
        print(f"!!! AI 에러: {str(e)}")
        return jsonify({"reply": "현재 서비스가 원활하지 않습니다. 잠시 후 시도해주세요."}), 500


# --- [기능 2] 이메일 발송 엔드포인트 ---
@app.route('/send-mail', methods=['POST'])
def send_mail():
    data = request.json
    try:
        sender_email = os.environ.get("SENDER_EMAIL")
        sender_pw = os.environ.get("SENDER_PW")
        admin_email = "jslee@rootlabs.co.kr"

        msg = MIMEMultipart()
        msg['From'] = f"ROOTLABS Contact <{sender_email}>"
        msg['To'] = admin_email
        msg['Subject'] = f"[홈페이지 문의] {data.get('subject')}"

        html_body = f"""
        <div style='font-family: sans-serif; padding: 20px; border: 1px solid #eee; max-width: 600px;'>
            <h2 style='color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px;'>신규 프로젝트 문의</h2>
            <p><b>성함/업체명:</b> {data.get('name')}</p>
            <p><b>회신 이메일:</b> {data.get('email')}</p>
            <div style='background: #f9f9f9; padding: 15px; margin-top: 15px; border-radius: 5px;'>
                <p><b>문의 상세 내용:</b></p>
                <p style='line-height: 1.6;'>{data.get('message').replace(chr(10), '<br>')}</p>
            </div>
            <p style='font-size: 12px; color: #888; margin-top: 20px;'>본 메일은 ROOTLABS 공식 홈페이지 시스템에서 발송되었습니다.</p>
        </div>
        """
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_pw)
            server.sendmail(sender_email, admin_email, msg.as_string())

        return jsonify({"result": "success"})
    except Exception as e:
        print(f"!!! 메일 에러: {e}")
        return jsonify({"result": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
