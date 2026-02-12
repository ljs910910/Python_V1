from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import os
import threading
import time
import requests
import logging
import openai
import io
import base64
import json
import traceback
import re
import warnings
from PIL import Image, ImageEnhance, ImageFont, ImageDraw, ImageColor
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ---------------------------
# [1] 환경 변수 로드 및 설정
# ---------------------------
load_dotenv()
warnings.filterwarnings("ignore")  # 불필요한 경고 메시지 숨기기

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not GOOGLE_API_KEY or not OPENAI_API_KEY:
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

# [시작 로그 출력]
logger.info("============== [서버 및 AI 엔진 가동 (범용 마스터 버전)] ==============")

# ---------------------------
# [2] AI 엔진 인증 (Gemini & Vertex AI)
# ---------------------------

# A. Gemini (두뇌) 설정
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("✅ Gemini API 인증 성공")
except Exception as e:
    logger.error(f"❌ Gemini 인증 실패: {e}")

# B. Vertex AI Imagen (손) 설정
# [중요] Render 환경변수 'GOOGLE_CREDENTIALS_JSON'에 JSON 내용을 그대로 넣었을 경우 처리
CREDENTIALS_JSON_CONTENT = os.environ.get("GOOGLE_CREDENTIALS_JSON")
KEY_FILE_NAME = "service-account.json"
KEY_PATH = os.path.join(BASE_DIR, KEY_FILE_NAME)

# 1. 환경변수에서 JSON 내용이 발견되면 파일로 생성 (Render 서버용)
if CREDENTIALS_JSON_CONTENT:
    try:
        with open(KEY_PATH, "w", encoding="utf-8") as f:
            f.write(CREDENTIALS_JSON_CONTENT)
        logger.info(f"📂 환경변수에서 인증 파일 생성 완료: {KEY_PATH}")
    except Exception as e:
        logger.error(f"❌ 인증 파일 생성 실패: {e}")

# 2. 파일 존재 여부 확인 후 환경변수 설정
if os.path.exists(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH
else:
    # 로컬 테스트용: 파일이 이미 있는지 확인 (gen-lang-client... 파일명 사용 시 수정 필요)
    # 만약 로컬 파일명이 다르다면 아래 이름을 본인 파일명으로 수정하세요.
    LOCAL_BACKUP_NAME = "rootai-486406-c497046479ff.json"
    LOCAL_BACKUP_PATH = os.path.join(BASE_DIR, LOCAL_BACKUP_NAME)

    if os.path.exists(LOCAL_BACKUP_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = LOCAL_BACKUP_PATH
        logger.info(f"📂 로컬 인증 파일 감지: {LOCAL_BACKUP_PATH}")
    else:
        logger.error("❌ 치명적 오류: 인증(JSON) 파일을 찾을 수 없습니다.")

# [프로젝트 ID 설정]
# 사용자의 JSON 파일 기준 프로젝트 ID
PROJECT_ID = os.environ.get("PROJECT_ID", "rootai-486406")
LOCATION = os.environ.get("LOCATION", "us-central1")

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    logger.info(f"✅ Vertex AI Imagen 인증 성공 (Project: {PROJECT_ID})")
except Exception as e:
    logger.error(f"❌ Vertex AI 인증 실패: {e}")

# ---------------------------
# [3] Flask 앱 설정
# ---------------------------
app = Flask(__name__)
# CORS 설정: 브라우저에서의 모든 요청 허용
CORS(app, resources={r"/*": {"origins": "*"}})

# 챗봇 모델 지정
VALID_MODEL = "gemini-2.5-flash"

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# 파일 확장자 체크
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def keep_alive():
    time.sleep(20)
    while True:
        try:
            requests.get(RENDER_EXTERNAL_URL, timeout=30)
        except:
            pass
        time.sleep(780)

# =======================================================
# [4] 신규 통합 기능: 이미지 생성 로직 (Vertex AI + Gemini)
# =======================================================
# --- 기능 1: 만능 텍스트 합성기 (슈퍼샘플링 적용: 화질 2배 강화) ---
def draw_text_overlay(image, text, position="BOTTOM_CENTER", is_title=False, requested_size=None, text_color="white",
                      stroke_color="black"):
    # 텍스트가 없거나 빈 문자열이면 바로 리턴
    if not text or not isinstance(text, str) or text.strip() == "":
        return image

    try:
        # [핵심 기술: 슈퍼샘플링]
        # 이미지를 2배로 뻥튀기해서 글씨를 쓰고 다시 줄이면 계단 현상이 사라지고 폰트가 쨍해집니다.
        original_w, original_h = image.size
        scale_factor = 2  # 2배 확대

        # 고품질 리사이징으로 캔버스 확대
        target_w, target_h = original_w * scale_factor, original_h * scale_factor
        upscaled_image = image.resize((target_w, target_h), Image.LANCZOS)

        draw = ImageDraw.Draw(upscaled_image)

        # 폰트 로드 (윈도우 맑은 고딕 우선 적용 -> 없으면 나눔고딕 -> 없으면 기본)
        font_path = "C:/Windows/Fonts/malgunbd.ttf"  # 맑은 고딕 볼드
        if not os.path.exists(font_path):
            font_path = "C:/Windows/Fonts/malgun.ttf"

        # 커스텀 폰트가 같은 폴더에 있다면 그걸 최우선으로
        custom_font = os.path.join(BASE_DIR, "Paperlogy-6SemiBold.ttf")
        if os.path.exists(custom_font):
            font_path = custom_font

        # 폰트 크기 결정 (캔버스가 2배 커졌으니 폰트도 2배 키워야 함)
        if requested_size is not None and isinstance(requested_size, int) and requested_size > 0:
            font_size = requested_size * scale_factor
        else:
            # 자동 비율: 제목은 8%, 부제는 4%
            font_size = int(target_w * (0.08 if is_title else 0.04))

        # 최소/최대 보정
        font_size = max(20, min(font_size, target_h))

        # 외곽선 두께
        stroke_width = max(2, int(font_size * 0.08))

        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            logger.warning("⚠️ 폰트 로드 실패, 기본 폰트 사용")
            font = ImageFont.load_default()

        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 글자가 이미지 너비를 넘으면 폰트 줄이기
        max_text_width = target_w * 0.9
        while text_w > max_text_width and font_size > 20:
            font_size = int(font_size * 0.95)
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            stroke_width = max(2, int(font_size * 0.08))

        # 여백 계산
        margin_x = int(target_w * 0.05)
        margin_y = int(target_h * 0.05)

        x, y = 0, 0
        pos = position.upper()

        if "LEFT" in pos:
            x = margin_x
        elif "RIGHT" in pos:
            x = target_w - text_w - margin_x
        else:
            x = (target_w - text_w) // 2

        if "TOP" in pos:
            y = margin_y
        elif "BOTTOM" in pos:
            y = target_h - text_h - margin_y
        else:
            y = (target_h - text_h) // 2

        # 텍스트 그리기
        try:
            draw.text((x, y), text, font=font, fill=text_color, stroke_width=stroke_width, stroke_fill=stroke_color)
        except Exception as color_error:
            logger.warning(f"⚠️ 색상 적용 실패 ({text_color}) -> 기본값 적용")
            draw.text((x, y), text, font=font, fill="white", stroke_width=stroke_width, stroke_fill="black")

        # 슈퍼샘플링 축소
        final_image = upscaled_image.resize((original_w, original_h), Image.LANCZOS)

        logger.info(f"✍️ [슈퍼샘플링 합성 완료] '{text}' ({font_size//scale_factor}px)")
        return final_image

    except Exception as e:
        logger.error(f"❌ 텍스트 합성 실패: {e}")
        return image


# --- 기능 2: Gemini (범용 스타일 & 로고 분석 - 핵심 지침) ---
def generate_universal_prompt(user_input):
    MODEL_NAME = "gemini-2.5-flash"
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        # [SYSTEM INSTRUCTION: 범용성, 화질, 로고 규칙의 집대성]
        system_instruction = """
        You are an expert AI Art Director. Your goal is to create precise visual instructions for ANY genre (Movie, Anime, Drama, Cartoon).

        [CRITICAL RULE 1: UNIVERSAL STYLE DETECTION]
        - Analyze the user's request to determine the **Visual Style Category**:
          - **"SIMPLE_2D"**: For simple cartoons, scribbles, children's content. (e.g., Crayon style, Stick figures).
          - **"HIGH_2D"**: For standard anime, manga, webtoons. (e.g., Cel-shading, detailed lines).
          - **"3D_RENDER"**: For 3D animation, claymation, game graphics. (e.g., Octane render, cute 3D).
          - **"REALISM"**: For live-action movies, TV dramas, documentaries. (e.g., 8k photo).

        [CRITICAL RULE 2: LOGO MATERIAL & COLOR (NO WHITE DEFAULT)]
        - **If the user asks for a Logo/Title:**
          - **DO NOT** default to a simple text overlay. Describe a **"Stylized Title Object"**.
          - **YOU MUST DEFINE THE MATERIAL & COLOR** of the logo based on the genre.
            - If "3D_RENDER": "A massive 3D title sculpture textured with **[Fur/Plastic/Slime]** in **[Bright Colors]**." (e.g., Orange Fur for Zootopia).
            - If "REALISM": "A cinematic **[Metallic/Stone/Neon]** title emblem with **[Rust/Glow]** effects." (e.g., Rusted Metal for Mad Max).
            - If "SIMPLE_2D": "A playful 2D graphic symbol made of **[Paper/Crayon/Sticker]** textures."
          - **Never leave the logo description as just 'A 3D Logo'.** It causes white text. Be specific.

        [CRITICAL RULE 3: TEXT DUPLICATION PREVENTION]
        - If you describe a logo object in the image, **LEAVE `title_text` EMPTY ("")**.
        - Do not overlay Python text on top of an image that already has a 3D logo object.

        [CRITICAL RULE 4: FORCE DEEP FOCUS (NO BLUR)]
        - **MANDATORY**: Unless the user asks for blur, always append these keywords:
          "**Shot on f/22 aperture, infinite depth of field, everything in sharp focus from foreground to background, crystal clear, no bokeh, wide angle lens.**"
        - Prevent the AI from applying "Cinematic Blur" automatically.

        [CRITICAL RULE 5: SAFETY (IP LAUNDERING)]
        - **NEVER** use specific copyrighted names (e.g. "Shin-chan", "Mickey", "Iron Man") in the output `visual_prompt`.
        - **Translate to Generic Descriptions**:
          - "Shin-chan" -> "A generic cute 2D cartoon boy with a round head".
          - "Iron Man" -> "A futuristic red and gold armored robot".

        [Output JSON]:
        {
          "style_category": "SIMPLE_2D" or "HIGH_2D" or "3D_RENDER" or "REALISM",
          "visual_prompt": "...",
          "title_text": "...", 
          "title_position": "TOP_CENTER", 
          "bottom_text": "...",
          "bottom_position": "BOTTOM_CENTER",
          "font_size_req": null or int,
          "text_color": "#RRGGBB",
          "stroke_color": "#RRGGBB"
        }
        """

        prompt = f"System: {system_instruction}\nUser Request: {user_input}"
        response = model.generate_content(prompt)
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)

    except Exception as e:
        logger.error(f"⚠️ Gemini 분석 오류: {e}")
        return {
            "style_category": "REALISM",  # 기본값
            "visual_prompt": f"High quality banner art of {user_input}, sharp focus, 8k, f/22 aperture, deep depth of field.",
            "title_text": "",
            "title_position": "TOP_CENTER",
            "bottom_text": "",
            "bottom_position": "BOTTOM_CENTER",
            "font_size_req": None,
            "text_color": "#FFFFFF",
            "stroke_color": "#000000"
        }


# --- 기능 3: 범용 스타일 필터 (부정 프롬프트) ---
def get_adaptive_negative_prompt(style_category):
    # 공통 부정어 (흐림 방지 포함)
    base_negative = "text, watermark, signature, username, error, writing, copyright, cropped, low quality, ugly, distorted, bad anatomy, overlapping, blending, blur, blurry, bokeh, shallow depth of field, tilt-shift, macro lens, cinematic blur, out of focus"

    if style_category == "SIMPLE_2D":
        # 단순 만화용: 고퀄리티 차단
        return f"{base_negative}, 3d, realistic, photorealistic, octane render, lighting, high quality details, gradient, cinematic, anime, manga"
    elif style_category == "HIGH_2D":
        # 애니메이션용: 실사 차단
        return f"{base_negative}, 3d, realistic, photorealistic, sketch, scribble, photo"
    elif style_category == "3D_RENDER":
        # 3D용: 2D 차단
        return f"{base_negative}, 2d, flat, cartoon, sketch, drawing, painting, vector, illustration, white text"
    elif style_category == "REALISM":
        # 실사용: 그림 차단
        return f"{base_negative}, cartoon, anime, 3d render, painting, drawing, illustration, sketch, fake, plastic"
    else:
        return base_negative


# --- 기능 4: Imagen 생성 엔진 (에어백 포함) ---
def generate_full_image(prompt, style_category, width, height):
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

    target_ratio = width / height
    supported_ratios = {"1:1": 1.0, "9:16": 0.5625, "16:9": 1.7778, "3:4": 0.75, "4:3": 1.3333}
    aspect_ratio = min(supported_ratios, key=lambda k: abs(supported_ratios[k] - target_ratio))

    negative_prompt = get_adaptive_negative_prompt(style_category)
    logger.info(f"🛡️ [스타일 필터] {style_category} 모드 작동")

    img_bytes = None

    # [1차 시도]
    try:
        logger.info(f"🎨 [1차 생성] {prompt[:100]}...")
        images = model.generate_images(
            prompt=prompt,
            negative_prompt=negative_prompt,
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            language="en"
        )
        first_image = next(iter(images), None)
        if not first_image: raise ValueError("Safety Filter triggered")
        img_bytes = first_image._image_bytes
    except Exception as e:
        if "429" in str(e): return "QUOTA_ERROR"
        logger.warning(f"⚠️ 1차 실패: {e}")

    # [2차 시도: 스타일별 자동 단순화]
    if not img_bytes:
        if style_category == "SIMPLE_2D":
            # 단순 만화는 더 단순하게
            fallback = f"A very simple, generic minimalist cartoon drawing, crayon style. Context: {prompt[:30]}"
            logger.info(f"🔄 [2차 재시도(단순화)] {fallback}")
        else:
            # 나머지는 일반적 묘사 (선명도 유지)
            fallback = f"High quality visual illustration, sharp focus, f/22 aperture, infinite depth of field. Context: {prompt[:50]}"
            logger.info(f"🔄 [2차 재시도(일반)] {fallback}")

        try:
            images = model.generate_images(
                prompt=fallback,
                negative_prompt=negative_prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                language="en"
            )
            first_image = next(iter(images), None)
            if not first_image: raise ValueError("Safety Filter triggered again")
            img_bytes = first_image._image_bytes
        except Exception as e:
            if "429" in str(e): return "QUOTA_ERROR"
            logger.warning(f"⚠️ 2차 실패: {e}")

    # [3차 시도: 최후의 보루]
    if not img_bytes:
        final_fallback = "A vivid, clear banner background art, professional design style, everything in sharp focus."
        try:
            logger.info(f"🚨 [3차 최후 시도] {final_fallback}")
            images = model.generate_images(
                prompt=final_fallback,
                negative_prompt=negative_prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                language="en"
            )
            first_image = next(iter(images), None)
            if not first_image: raise ValueError("Critical Failure")
            img_bytes = first_image._image_bytes
        except Exception as e:
            if "429" in str(e): return "QUOTA_ERROR"
            return None

    try:
        if not img_bytes: return None
        img = Image.open(io.BytesIO(img_bytes))
        final_img = img.resize((width, height), Image.LANCZOS)

        # 선명도/대비 보정 (배경 쨍하게 +1.5배)
        final_img = ImageEnhance.Sharpness(final_img).enhance(1.5)
        final_img = ImageEnhance.Contrast(final_img).enhance(1.2)
        final_img = ImageEnhance.Color(final_img).enhance(1.15)

        return final_img
    except Exception as e:
        logger.error(f"❌ 이미지 후처리 실패: {e}")
        return None


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
# [엔드포인트] AI 챗봇 (기존 소스 A 유지)
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
# [엔드포인트] 이미지 생성
# ---------------------------
@app.route("/generate-image", methods=["POST"])
def generate_auto_banner():
    import traceback
    try:
        logger.info("===== 🔵 /generate-image START =====")

        # 1️⃣ JSON 강제 파싱 (조용히 실패하는 것 방지)
        data = request.get_json(force=True, silent=False)
        logger.info(f"📦 Raw JSON: {data}")

        if not isinstance(data, dict):
            raise ValueError("JSON 데이터가 dict가 아님")

        raw_input = str(data.get("prompt", "")).strip()
        size_input = str(data.get("size", "1480x600"))

        # 🔐 format 방어
        FORMAT_MAP = {
            "JPG": "JPEG",
            "JPEG": "JPEG",
            "PNG": "PNG"
        }

        input_format = str(data.get("format", "PNG")).strip().upper()
        img_format = FORMAT_MAP.get(input_format, "PNG")

        logger.info(f"🖼 Format 요청값: {input_format} → 저장포맷: {img_format}")

        # 2️⃣ 사이즈 파싱
        try:
            if "x" in size_input.lower():
                w, h = map(int, size_input.lower().split("x"))
            else:
                w = h = int(size_input)
        except Exception as e:
            logger.warning(f"⚠️ 사이즈 파싱 실패 → 기본값 사용: {e}")
            w, h = 1480, 600

        logger.info(f"📐 Size: {w}x{h}")

        # 3️⃣ 프롬프트 분석
        ai_result = generate_universal_prompt(raw_input) or {}
        logger.info(f"🧠 AI 분석 결과: {ai_result}")

        style_category = ai_result.get("style_category", "REALISM")
        visual_prompt = ai_result.get("visual_prompt")

        title_text = ai_result.get("title_text")
        title_pos = ai_result.get("title_position", "TOP_CENTER")
        bottom_text = ai_result.get("bottom_text")
        bottom_pos = ai_result.get("bottom_position", "BOTTOM_CENTER")

        font_size_req = ai_result.get("font_size_req")
        text_color = ai_result.get("text_color", "#FFFFFF")
        stroke_color = ai_result.get("stroke_color", "#000000")

        if not visual_prompt:
            raise ValueError("visual_prompt 생성 실패")

        logger.info(f"🎨 이미지 생성 시작")

        # 4️⃣ 이미지 생성
        final_img = generate_full_image(visual_prompt, style_category, w, h)

        if final_img == "QUOTA_ERROR":
            logger.warning("⚠️ QUOTA 초과")
            return jsonify({
                "error": "사용량 초과. 잠시 후 다시 시도해주세요."
            }), 429

        if final_img is None:
            raise RuntimeError("generate_full_image()가 None 반환")

        logger.info(f"🖼 이미지 생성 완료 | mode={final_img.mode}")

        # 5️⃣ 텍스트 합성
        if title_text and str(title_text).strip():
            logger.info("✍️ 타이틀 합성")
            final_img = draw_text_overlay(
                final_img,
                title_text,
                position=title_pos,
                is_title=True,
                requested_size=font_size_req,
                text_color=text_color,
                stroke_color=stroke_color
            )

        if bottom_text and str(bottom_text).strip():
            logger.info("✍️ 하단 텍스트 합성")
            final_img = draw_text_overlay(
                final_img,
                bottom_text,
                position=bottom_pos,
                is_title=False,
                requested_size=font_size_req,
                text_color=text_color,
                stroke_color=stroke_color
            )

        # 6️⃣ 저장
        logger.info("💾 이미지 저장 시작")

        byte_arr = io.BytesIO()

        if img_format == "JPEG":
            if final_img.mode != "RGB":
                logger.info(f"🔄 RGB 변환 ({final_img.mode} → RGB)")
                final_img = final_img.convert("RGB")

        final_img.save(byte_arr, format=img_format)
        byte_arr.seek(0)

        encoded_img = base64.b64encode(byte_arr.read()).decode("utf-8")

        logger.info("✅ 이미지 저장 완료")

        logger.info("===== 🟢 SUCCESS =====")

        return jsonify({
            "image_url": f"data:image/{img_format.lower()};base64,{encoded_img}",
            "status": "success"
        })

    except Exception as e:
        logger.error("❌❌❌ 서버 에러 발생 ❌❌❌")
        logger.error(str(e))
        logger.error(traceback.format_exc())

        return jsonify({
            "error": "서버 내부 오류",
            "detail": str(e)
        }), 500

# ---------------------------
# [엔드포인트] 이미지 수정 (Vertex AI + Gemini + 스타일 필터 + 텍스트 합성)
# ---------------------------
@app.route("/edit-image", methods=["POST"])
def edit_image():
    # ---------------------------------------------------------
    # [필수 임포트] 상단에 없는 라이브러리만 여기서 임포트합니다.
    # ---------------------------------------------------------
    import tempfile 
    from vertexai.preview.vision_models import Image as VertexImage # Vertex AI 이미지 래퍼 클래스

    try:
        print("\n========== [edit_image] 요청 진입 ==========")

        # 1️⃣ 파일 및 폼 데이터 확인
        if "image" not in request.files:
            raise ValueError("❌ 데이터 누락: image 파일이 없습니다.")
        if "prompt" not in request.form:
            raise ValueError("❌ 데이터 누락: prompt가 없습니다.")

        img_file = request.files["image"]
        raw_prompt = request.form["prompt"].strip()
        size_input = request.form.get("size", "1480x600")
        format_input = request.form.get("format", "PNG").upper()

        print(f"👉 프롬프트: {raw_prompt} | 사이즈: {size_input} | 포맷: {format_input}")

        # 2️⃣ 사이즈 파싱
        try:
            if "x" in size_input.lower():
                w, h = map(int, size_input.lower().split("x"))
            else:
                w = h = int(size_input)
        except:
            w, h = 1480, 600
        print(f"📐 이미지 최종 사이즈: {w}x{h}")

        # 3️⃣ 🔥 핵심 수정: 임시 파일 저장으로 에러 원천 차단
        # Vertex AI SDK는 파일 경로(load_from_file)를 통해 객체를 생성할 때 가장 안정적입니다.
        # BytesIO 객체를 직접 넘기면 '_gcs_uri' 속성 에러가 발생하므로 이를 우회합니다.
        temp_path = None
        filename = secure_filename(img_file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), f"edit_{int(time.time())}_{filename}")
        img_file.save(temp_path)

        try:
            # Vertex AI 전용 이미지 객체 생성
            vertex_image = VertexImage.load_from_file(temp_path)

            # 4️⃣ Gemini 분석 (프롬프트 최적화 및 스타일 추출)
            try:
                ai_result = generate_universal_prompt(raw_prompt)
                visual_prompt = ai_result.get("visual_prompt", raw_prompt)
                style_category = ai_result.get("style_category", "REALISM")
                title_text = ai_result.get("title_text", "")
                title_pos = ai_result.get("title_position", "TOP_CENTER")
                bottom_text = ai_result.get("bottom_text", "")
                bottom_pos = ai_result.get("bottom_position", "BOTTOM_CENTER")
                font_size_req = ai_result.get("font_size_req")
                text_color = ai_result.get("text_color", "#FFFFFF")
                stroke_color = ai_result.get("stroke_color", "#000000")
                print("✅ Gemini 분석 완료")
            except Exception as e:
                print(f"⚠️ Gemini 분석 실패(기본값 사용): {e}")
                visual_prompt = raw_prompt
                style_category = "REALISM"
                title_text, bottom_text = "", ""
                title_pos, bottom_pos = "TOP_CENTER", "BOTTOM_CENTER"
                font_size_req, text_color, stroke_color = None, "#FFFFFF", "#000000"

            # 5️⃣ Vertex AI Imagen 모델 호출 (이미지 수정 실행)
            # 상단에 ImageGenerationModel이 임포트 되어 있다고 가정합니다.
            model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
            negative_prompt = get_adaptive_negative_prompt(style_category)
            print("🎨 Vertex AI Imagen 이미지 수정 요청 전송...")

            response = model.edit_image(
                base_image=vertex_image,
                prompt=visual_prompt,
                negative_prompt=negative_prompt,
                number_of_images=1,
                language="en",
            )

            if not response.images:
                raise ValueError("❌ AI가 이미지를 반환하지 않았습니다. (Safety Filter 가능성)")

            # 결과 이미지를 PIL 객체로 변환
            final_img = response.images[0]._pil_image

            # 6️⃣ 이미지 후처리: 리사이즈 및 화질 개선
            final_img = final_img.resize((w, h), Image.LANCZOS)
            final_img = ImageEnhance.Sharpness(final_img).enhance(1.5)
            final_img = ImageEnhance.Contrast(final_img).enhance(1.2)
            final_img = ImageEnhance.Color(final_img).enhance(1.15)

            # 7️⃣ 텍스트 합성 (타이틀 + 하단 문구)
            if title_text.strip():
                final_img = draw_text_overlay(
                    final_img, title_text, position=title_pos, is_title=True,
                    requested_size=font_size_req, text_color=text_color, stroke_color=stroke_color
                )

            if bottom_text.strip():
                final_img = draw_text_overlay(
                    final_img, bottom_text, position=bottom_pos, is_title=False,
                    requested_size=font_size_req, text_color=text_color, stroke_color=stroke_color
                )

            # 8️⃣ 결과 반환 처리 (포맷 변환 및 Base64 인코딩)
            FORMAT_MAP = {"JPG": "JPEG", "JPEG": "JPEG", "PNG": "PNG"}
            img_format = FORMAT_MAP.get(format_input, "PNG")

            byte_arr = io.BytesIO()
            if img_format == "JPEG" and final_img.mode != "RGB":
                final_img = final_img.convert("RGB")

            final_img.save(byte_arr, format=img_format)
            byte_arr.seek(0)

            encoded_img = base64.b64encode(byte_arr.read()).decode("utf-8")
            print("🚀 이미지 수정 완료 및 전송 준비")

            return jsonify({
                "image_url": f"data:image/{img_format.lower()};base64,{encoded_img}",
                "status": "success"
            })

        finally:
            # 사용이 끝난 임시 파일 삭제 (서버 용량 관리)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n🚨 [edit_image] 서버 에러 발생:\n{error_trace}")
        return jsonify({
            "error": f"서버 에러: {str(e)}",
            "detail": error_trace
        }), 500

# ---------------------------
# [엔드포인트] 메일 서버 (기존 소스 A 유지)
# ---------------------------
POSTMARK_API_KEY = os.environ.get("POSTMARK_API_KEY")
SENDER_EMAIL = "jslee@rootlabs.co.kr"  # 인증된 발신자 이메일
RECIPIENT_EMAIL = "jslee@rootlabs.co.kr"

@app.route("/send-mail", methods=["POST"])
def send_mail():
    data = request.json
    try:
        resp = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": POSTMARK_API_KEY
            },
            json={
                "From": SENDER_EMAIL,
                "To": RECIPIENT_EMAIL,
                "Subject": f"[홈페이지 문의] {data.get('subject')}",
                "TextBody": f"""
성함: {data.get('name')}
이메일: {data.get('email')}

문의 내용:
{data.get('message')}
"""
            }
        )

        if resp.status_code == 200:
            return jsonify({"result": "success"})
        else:
            return jsonify({
                "result": "error",
                "message": resp.json().get("Message", "메일 발송 실패")
            }), resp.status_code

    except Exception as e:
        return jsonify({"result": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return "ROOTLABS Unified AI Server is Online"

if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

