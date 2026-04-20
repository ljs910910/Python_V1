from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import pymysql
import string
import random
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import os
import threading
import time
from datetime import datetime, timedelta
import requests
import logging
import openai
import io
import base64
import json
import warnings
from PIL import Image, ImageEnhance, ImageFont, ImageDraw, ImageColor
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
# --- 기능 1: 만능 텍스트 합성기 (슈퍼샘플링 + 폰트 확대 + 다중 줄바꿈 + 유동적 정렬) ---
def draw_text_overlay(image, text, position="BOTTOM_CENTER", is_title=False, requested_size=None, text_color="white",
                      stroke_color="black"):
    if not text or not isinstance(text, str) or text.strip() == "":
        return image

    try:
        # [1] 줄바꿈 정규화: AI가 \n을 문자열로 보낼 경우를 대비해 실제 줄바꿈으로 변환
        text = text.replace("\\n", "\n")

        # [2] 슈퍼샘플링 (화질 저하 방지용 2배 확대)
        original_w, original_h = image.size
        scale_factor = 2
        target_w, target_h = original_w * scale_factor, original_h * scale_factor
        upscaled_image = image.resize((target_w, target_h), Image.LANCZOS)
        draw = ImageDraw.Draw(upscaled_image)

        # 폰트 로드 설정
        font_path = "C:/Windows/Fonts/malgunbd.ttf"
        if not os.path.exists(font_path): font_path = "C:/Windows/Fonts/malgun.ttf"
        custom_font = os.path.join(BASE_DIR, "Paperlogy-6SemiBold.ttf")
        if os.path.exists(custom_font): font_path = custom_font

        # [3] 초기 폰트 크기 설정 (비율 넉넉하게 상향! 기존 8%->15%, 4%->8%)
        ref_size = min(target_w, target_h)
        if requested_size is not None and isinstance(requested_size, int) and requested_size > 0:
            font_size = requested_size * scale_factor
        else:
            font_size = int(ref_size * (0.15 if is_title else 0.08))

        # [4] 사용자의 명시적 줄바꿈을 유지하면서 크기만 최적화
        max_width = target_w * 0.90
        max_height = target_h * 0.40  # 텍스트가 차지할 수 있는 최대 높이 설정

        while font_size >= 20:
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
                break

            stroke_width = max(2, int(font_size * 0.08))
            line_spacing = int(font_size * 0.2)

            # 명시된 텍스트 전체 덩어리의 크기를 측정 (멀티라인 전용 함수 사용)
            bbox = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=stroke_width, spacing=line_spacing)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 텍스트 덩어리가 캔버스 안에 예쁘게 들어오면 스톱
            if text_w <= max_width and text_h <= max_height:
                break
            else:
                # 넘어간다면 폰트 크기를 5%씩 점진적으로 축소
                font_size = int(font_size * 0.95)

        # [5] 위치 및 동적 정렬(Align) 계산
        margin_x = int(target_w * 0.05)
        margin_y = int(target_h * 0.05)
        x, y = 0, 0
        pos = position.upper()

        # 기본 정렬 설정
        text_align = "center"

        # 좌우 위치에 따른 x좌표 및 텍스트 내부 정렬(align) 동기화
        if "LEFT" in pos:
            x = margin_x
            text_align = "left"
        elif "RIGHT" in pos:
            x = target_w - text_w - margin_x
            text_align = "right"
        else:
            x = (target_w - text_w) // 2
            text_align = "center"

        # 상하 위치 계산
        if "TOP" in pos:
            y = margin_y
        elif "BOTTOM" in pos:
            y = target_h - text_h - margin_y
        else:
            y = (target_h - text_h) // 2

        # 최종 텍스트 그리기 (위치에 따라 동적으로 변하는 align 적용)
        try:
            draw.multiline_text((x, y), text, font=font, fill=text_color, stroke_width=stroke_width,
                                stroke_fill=stroke_color, spacing=line_spacing, align=text_align)
        except Exception as color_error:
            logger.warning(f"⚠️ 색상 적용 실패 ({text_color}) -> 기본값 적용")
            draw.multiline_text((x, y), text, font=font, fill="white", stroke_width=stroke_width, stroke_fill="black",
                                spacing=line_spacing, align=text_align)

        # 슈퍼샘플링 축소 및 결과 반환
        final_image = upscaled_image.resize((original_w, original_h), Image.LANCZOS)
        logger.info(f"✍️ [텍스트 합성 완료] '{text[:10]}...' ({font_size // scale_factor}px, Align: {text_align})")
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

        [CRITICAL RULE 6: TEXT LINE BREAKS]
        - If the user provides multiple quoted strings (e.g., "Line 1" "Line 2") or requests line breaks, you MUST combine them using the `\n` character in `title_text` or `bottom_text` (e.g., "Line 1\nLine 2"). Do not include the quotes in the output string.

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
    # [⭐ 삽입/수정됨] 텍스트 렌더링 오류(bad text, garbage), 형태 붕괴(deformed, artifact) 방지 키워드 대폭 추가
    base_negative = "bad text, garbage, gibberish, artifact, deformed, text, watermark, signature, username, error, writing, copyright, cropped, low quality, ugly, distorted, bad anatomy, overlapping, blending, blur, blurry, bokeh, shallow depth of field, tilt-shift, macro lens, cinematic blur, out of focus"

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
    model = ImageGenerationModel.from_pretrained("imagen-4.0-ultra-generate-001")

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
            negative_prompt=negative_prompt, # ⭐ 위에서 보강된 네거티브 프롬프트가 여기서 주입됨
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            language="en",
            # [⭐ 삽입됨] 인물 생성 시 구글의 안전 필터로 인해 튕기는 빈도를 줄여주는 파라미터 옵션 추가
            person_generation="ALLOW_ADULT"
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
                language="en",
                person_generation="ALLOW_ADULT" # ⭐ 삽입됨
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
        - "현재 루트랩스는 고도의 생성형 AI 기술을 활용한 맞춤형 이미지 제작 솔 파트너..." 등등
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
    import re  # 쌍따옴표 추출을 위한 정규표현식 모듈 추가
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

        raw_title_text = ai_result.get("title_text", "")
        title_pos = ai_result.get("title_position", "TOP_CENTER")
        raw_bottom_text = ai_result.get("bottom_text", "")
        bottom_pos = ai_result.get("bottom_position", "BOTTOM_CENTER")

        font_size_req = ai_result.get("font_size_req")
        text_color = ai_result.get("text_color", "#FFFFFF")
        stroke_color = ai_result.get("stroke_color", "#000000")

        if not visual_prompt:
            raise ValueError("visual_prompt 생성 실패")

        # =======================================================
        # [🌟 핵심 추가 로직] 쌍따옴표(" ") 기반 명시적 줄바꿈 처리
        # =======================================================
        def format_text_lines(text_data):
            if not text_data:
                return ""

            text_str = str(text_data).strip()

            # 1) 문자열 내에 쌍따옴표(" ")로 묶인 텍스트 그룹 찾기
            matches = re.findall(r'"([^"]+)"', text_str)

            if len(matches) > 1:
                # 예: '"TEST 한줄" "TEST 두줄"' -> 줄바꿈(\n)으로 합침
                return "\n".join(matches)
            elif len(matches) == 1:
                # 쌍따옴표가 하나만 있다면 껍데기만 벗겨냄
                text_str = matches[0]

            # 2) AI가 의도적으로 텍스트 내에 \n을 텍스트 형태로 보낸 경우를 위한 대비책
            return text_str.replace("\\n", "\n")

        # 텍스트 데이터 정제 실행
        title_text = format_text_lines(raw_title_text)
        bottom_text = format_text_lines(raw_bottom_text)

        logger.info(f"📝 최종 텍스트 추출 완료 - Title: {repr(title_text)} / Bottom: {repr(bottom_text)}")

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
# [엔드포인트] 진정한 범용 정밀 수정 (배경/사물 모드 자동 스위칭 완결판)
# ---------------------------
@app.route("/edit-image", methods=["POST"])
def edit_image():
    import traceback, io, base64, json, re
    from PIL import Image, ImageEnhance
    import requests
    import google.auth
    import google.auth.transport.requests

    try:
        logger.info("\n========== [Universal Master] 지능형 모드 스위칭 엔진 가동 ==========")

        img_file = request.files.get("image")
        raw_prompt = request.form.get("prompt", "").strip()
        size_input = request.form.get("size", "1480x600")

        if not img_file:
            return jsonify({"error": "이미지 파일이 없습니다."}), 400

        # 1️⃣ [이미지 전처리] (기존 규격 유지)
        orig_w, orig_h = 0, 0
        img_b64 = ""
        with Image.open(img_file) as img:
            if img.mode in ("RGBA", "LA", "P"):
                canvas = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    canvas.paste(img, mask=img.split()[3])
                else:
                    canvas.paste(img.convert("RGBA"))
                rgb_img = canvas
            else:
                rgb_img = img.convert("RGB")
            orig_w, orig_h = rgb_img.size
            ai_ready = rgb_img.resize((1024, 1024), Image.LANCZOS)
            img_byte_arr = io.BytesIO()
            ai_ready.save(img_byte_arr, format="JPEG", quality=95)
            img_b64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

        # 2️⃣ 🧠 [Gemini] 동적 모드 결정 및 시맨틱 타겟팅
        model_gemini = genai.GenerativeModel("gemini-2.5-flash")
        analysis_prompt = f"""
        User request: "{raw_prompt}"

        Analyze the request and return JSON ONLY:
        {{ "prompt": "...", "mask_target": "...", "mask_mode": "..." }}

        [STRATEGY GUIDE]
        1. If the user wants to change the ENVIRONMENT/SCENERY/BACKGROUND:
           - 'mask_mode': "BACKGROUND"
           - 'mask_target': "the entire background and scenery excluding the characters and the top-center logo"
           - 'prompt': Describe the new background in detail + "Strictly preserve original subjects."
        2. If the user wants to add/change an OBJECT, CHARACTER, or LOGO:
           - 'mask_mode': "FOREGROUND"
           - 'mask_target': "the specific object or the empty space for addition"
           - 'prompt': Describe the change + "Seamlessly blend with original background."
        """
        res_gemini = model_gemini.generate_content(analysis_prompt)

        # JSON 안전 파싱
        json_match = re.search(r'\{.*\}', res_gemini.text, re.DOTALL)
        if json_match:
            try:
                dec = json.loads(json_match.group())
            except:
                dec = {"prompt": raw_prompt, "mask_target": "background", "mask_mode": "BACKGROUND"}
        else:
            dec = {"prompt": raw_prompt, "mask_target": "background", "mask_mode": "BACKGROUND"}

        v_prompt = dec.get("prompt", raw_prompt)
        v_mask_target = dec.get("mask_target", "the environment")
        v_mask_mode = str(dec.get("mask_mode", "BACKGROUND")).upper()

        logger.info(f"🎯 선택된 모드: {v_mask_mode} | 타겟팅: {v_mask_target}")

        # 3️⃣ 🚀 [REST API] 시맨틱 정밀 통신
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials, _ = google.auth.default(scopes=scopes)
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        access_token = credentials.token

        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/imagen-3.0-capability-001:predict"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        payload = {
            "instances": [
                {
                    "prompt": v_prompt,
                    "referenceImages": [
                        {
                            "referenceType": "REFERENCE_TYPE_RAW",
                            "referenceId": 1,
                            "referenceImage": {"bytesBase64Encoded": img_b64}
                        },
                        {
                            "referenceType": "REFERENCE_TYPE_MASK",
                            "referenceId": 2,
                            "maskImageConfig": {
                                "maskMode": f"MASK_MODE_{v_mask_mode}",
                                "maskPrompt": v_mask_target
                            }
                        }
                    ]
                }
            ],
            "parameters": {
                "sampleCount": 1,
                "editMode": "EDIT_MODE_INPAINT_INSERTION",
                # [⭐ 삽입됨] REST API를 통한 이미지 수정 시에도 쓰레기 텍스트 생성이나 형태 붕괴를 막기 위해 강력한 부정 프롬프트를 명시합니다.
                "negativePrompt": "bad text, garbage, gibberish, artifact, deformed, blurry, low quality, watermark, signature, ugly, distorted"
            }
        }

        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200: raise RuntimeError(f"API Error: {resp.text}")

        out_b64 = resp.json().get("predictions", [{}])[0].get("bytesBase64Encoded")

        # 4️⃣ [후처리] (기존 로직 유지)
        final_img = Image.open(io.BytesIO(base64.b64decode(out_b64)))
        final_img = final_img.resize((orig_w, orig_h), Image.LANCZOS)
        try:
            tw, th = map(int, size_input.lower().split("x")) if "x" in size_input.lower() else (1480, 600)
            final_img = final_img.resize((tw, th), Image.LANCZOS)
        except:
            pass

        final_img = ImageEnhance.Sharpness(final_img).enhance(1.4)

        byte_arr = io.BytesIO()
        final_img.save(byte_arr, format="PNG")
        encoded = base64.b64encode(byte_arr.getvalue()).decode("utf-8")

        logger.info("✅ 범용 정밀 수정 완료!")
        return jsonify({"image_url": f"data:image/png;base64,{encoded}", "status": "success"})

    except Exception as e:
        logger.error(f"❌ 수정 실패: {str(e)}")
        return jsonify({"error": "수정 실패", "detail": str(e)}), 500

# ---------------------------
# [엔드포인트] 메일 서버
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


# ---------------------------
# [엔드포인트] 회원가입
# ---------------------------
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
DB_PORT = int(os.environ.get("DB_PORT", 23155))

# [3] DB 연결 함수 정의 (라우트보다 위에 있어야 함!)
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        ssl={"ssl": {}}
    )

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"result": "fail", "message": "모든 필드를 입력해주세요."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. 이메일 중복 체크
            check_sql = "SELECT id FROM users WHERE email = %s"
            cursor.execute(check_sql, (email,))
            if cursor.fetchone():
                return jsonify({"result": "fail", "message": "이미 가입된 이메일입니다."}), 409

            # 2. 비밀번호 암호화 (단방향 해시)
            hashed_password = generate_password_hash(password)

            # 3. DB에 회원 정보 INSERT
            insert_sql = "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)"
            cursor.execute(insert_sql, (email, hashed_password, name))

        # 4. DB 변경사항 커밋(저장)
        connection.commit()
        return jsonify({"result": "success", "message": "회원가입 성공"}), 201

    except Exception as e:
        logger.error(f"Signup DB Error: {str(e)}")
        # 에러 발생 시 DB 롤백
        if connection:
            connection.rollback()
        return jsonify({"result": "error", "message": "회원가입 처리 중 서버 오류가 발생했습니다."}), 500

    finally:
        if connection:
            connection.close()

# ---------------------------
# Aiven DB Sleep 방지용 Ping Job
# ---------------------------
def db_ping_job():
    """6시간마다 DB에 연결하여 SELECT 1을 실행하여 Sleep 상태를 방지합니다."""
    connection = None
    try:
        logger.info("⏰ [DB Ping Job] Aiven DB Sleep 방지 핑 시작...")
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.info(f"✅ [DB Ping Job] Ping 성공! Result: {result}")
    except Exception as e:
        logger.error(f"❌ [DB Ping Job] Ping 실패: {str(e)}")
    finally:
        if connection:
            connection.close()

# ---------------------------
# 스케줄러 초기화 및 시작
# ---------------------------
# Flask 앱 시작 시 스케줄러를 백그라운드로 실행하도록 설정합니다.
scheduler = BackgroundScheduler(daemon=True)
# 6시간(360분) 간격으로 db_ping_job 실행
scheduler.add_job(db_ping_job, 'interval', hours=6, id='aiven_db_keep_alive')
scheduler.start()
logger.info("⏱️ 백그라운드 스케줄러(APScheduler) 가동 완료: 6시간 주기로 DB Ping 실행")

# ---------------------------
# [엔드포인트] 로그인
# ---------------------------
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"result": "fail", "message": "이메일과 비밀번호를 입력해주세요."}), 400

    connection = None
    try:
        # 1. DB 연결
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # ⭐ 수정: 이메일로 사용자 정보 조회 시 'role' 컬럼 추가
            sql = "SELECT id, email, password_hash, name, role FROM users WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

        # 3. 사용자 검증 (이메일 존재 확인 및 비밀번호 해시 일치 여부 확인)
        if user and check_password_hash(user['password_hash'], password):
            # 로그인 성공 시
            return jsonify({
                "result": "success",
                "message": "로그인 성공",
                "name": user['name'],
                "role": user['role'], # ⭐ 수정: DB에서 가져온 role 값을 프론트엔드 응답에 포함
                "token": "sample_jwt_token_here"
            }), 200
        else:
            # 로그인 실패 시
            return jsonify({"result": "fail", "message": "이메일 또는 비밀번호가 일치하지 않습니다."}), 401

    except Exception as e:
        logger.error(f"DB Error: {str(e)}")
        return jsonify({"result": "error", "message": "서버 통신 오류가 발생했습니다."}), 500

    finally:
        # DB 연결 종료 (필수)
        if connection:
            connection.close()

# ---------------------------
# [엔드포인트] 비밀번호 찾기 (임시 비밀번호 발급)
# ---------------------------
@app.route('/find-password', methods=['POST'])
def find_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"result": "fail", "message": "이메일을 입력해주세요."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. 가입된 이메일인지 확인
            sql = "SELECT id, name FROM users WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"result": "fail", "message": "등록되지 않은 이메일입니다."}), 404

            # 2. 임시 비밀번호 생성 (8자리 영문+숫자)
            chars = string.ascii_letters + string.digits
            temp_password = ''.join(random.choice(chars) for i in range(8))
            hashed_temp_password = generate_password_hash(temp_password)

            # 3. DB에 임시 비밀번호 업데이트
            update_sql = "UPDATE users SET password_hash = %s WHERE email = %s"
            cursor.execute(update_sql, (hashed_temp_password, email))
            connection.commit()

            # 4. 임시 비밀번호를 이메일로 발송 (Postmark API 활용)
            # 기존에 /send-mail 라우트에서 사용하시는 POSTMARK_API_KEY와 발송 로직을 그대로 사용합니다.
            POSTMARK_API_KEY = os.environ.get("POSTMARK_API_KEY")
            SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "jslee@rootlabs.co.kr") # 인증된 발신자

            resp = requests.post(
                "https://api.postmarkapp.com/email",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": POSTMARK_API_KEY
                },
                json={
                    "From": SENDER_EMAIL,
                    "To": email,
                    "Subject": "[루트랩스] 임시 비밀번호 발급 안내",
                    "TextBody": f"""
안녕하세요, {user['name']}님.
요청하신 루트랩스 계정의 임시 비밀번호가 발급되었습니다.

임시 비밀번호: {temp_password}

로그인 후 반드시 비밀번호를 변경해 주시기 바랍니다.
감사합니다.
"""
                }
            )

            # 메일 발송이 실패하더라도 일단 DB는 업데이트 되었으므로 에러처리는 필요에 따라 보강합니다.
            if resp.status_code != 200:
                logger.warning(f"메일 발송 실패: {resp.text}")

        return jsonify({"result": "success", "message": "임시 비밀번호 발송 완료"}), 200

    except Exception as e:
        logger.error(f"Find Password Error: {str(e)}")
        if connection:
            connection.rollback()
        return jsonify({"result": "error", "message": "서버 통신 오류가 발생했습니다."}), 500

    finally:
        if connection:
            connection.close()


# ---------------------------
# [엔드포인트] 비밀번호 변경
# ---------------------------
@app.route('/change-password', methods=['POST'])
def change_password():
    data = request.get_json()
    email = data.get('email')
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not email or not current_password or not new_password:
        return jsonify({"result": "fail", "message": "모든 항목을 입력해주세요."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. DB에서 사용자 정보 가져오기
            sql = "SELECT id, password_hash FROM users WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"result": "fail", "message": "가입되지 않은 이메일입니다."}), 404

            # 2. 현재 비밀번호 일치 여부 검증
            if not check_password_hash(user['password_hash'], current_password):
                return jsonify({"result": "fail", "message": "현재 비밀번호가 일치하지 않습니다."}), 401

            # 3. 새 비밀번호 암호화 및 DB 업데이트
            hashed_new_password = generate_password_hash(new_password)

            update_sql = "UPDATE users SET password_hash = %s WHERE email = %s"
            cursor.execute(update_sql, (hashed_new_password, email))
            connection.commit()

        return jsonify({"result": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}), 200

    except Exception as e:
        logger.error(f"Change Password Error: {str(e)}")
        if connection:
            connection.rollback()
        return jsonify({"result": "error", "message": "서버 통신 오류가 발생했습니다."}), 500

    finally:
        if connection:
            connection.close()

# ---------------------------
# [엔드포인트] (공통) 내 연차 정보 조회
# ---------------------------
@app.route('/api/leave/my-info', methods=['POST'])
def get_my_leave_info():
    """로그인한 사용자의 총 연차와 사용 연차를 반환합니다."""
    # 현재 토큰 인증이 없으므로, 프론트에서 이메일을 보내도록 처리 (보안상 임시)
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"result": "fail", "message": "사용자 정보가 필요합니다."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT total_leave, used_leave FROM users WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"result": "fail", "message": "사용자를 찾을 수 없습니다."}), 404

            return jsonify({
                "result": "success",
                "total_leave": user['total_leave'],
                "used_leave": user['used_leave']
            }), 200
    except Exception as e:
        logger.error(f"연차 조회 오류: {str(e)}")
        return jsonify({"result": "error", "message": "서버 통신 오류"}), 500
    finally:
        if connection: connection.close()

# ---------------------------
# [엔드포인트] (직원) 휴가 신청
# ---------------------------
@app.route('/api/leave/apply', methods=['POST'])
def apply_leave():
    data = request.get_json()
    email = data.get('email')
    leave_type = data.get('leave_type')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    reason = data.get('reason')

    if not all([email, leave_type, start_date, end_date, reason]):
        return jsonify({"result": "fail", "message": "모든 항목을 입력해주세요."}), 400

    # ⭐ 연차 차감 일수 자동 계산 로직 (버그 픽스)
    deduction = 0.0
    if leave_type == '연차':
        try:
            s_date = datetime.strptime(start_date, '%Y-%m-%d')
            e_date = datetime.strptime(end_date, '%Y-%m-%d')
            deduction = float((e_date - s_date).days + 1)
        except Exception as e:
            logger.error(f"날짜 파싱 오류: {e}")
            deduction = 1.0
    elif leave_type in ['오전반차', '오후반차']:
        deduction = 0.5
    # 공가는 차감 안 함 (0.0)

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user: return jsonify({"result": "fail", "message": "사용자 없음"}), 404

            insert_sql = """
                INSERT INTO leave_requests (user_id, leave_type, start_date, end_date, deduction_days, reason, status)
                VALUES (%s, %s, %s, %s, %s, %s, '대기')
            """
            cursor.execute(insert_sql, (user['id'], leave_type, start_date, end_date, deduction, reason))
            connection.commit()

        return jsonify({"result": "success", "message": "휴가 신청이 접수되었습니다."}), 201
    except Exception as e:
        logger.error(f"휴가 신청 오류: {str(e)}")
        if connection: connection.rollback()
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()


# ---------------------------
# [엔드포인트] (관리자) 직원 연차 일수 부여
# ---------------------------
@app.route('/api/admin/grant-leave', methods=['POST'])
def grant_leave():
    """관리자가 특정 직원 이메일로 연차 일수를 부여(누적)하고 권한을 staff로 올립니다."""
    data = request.get_json()
    admin_email = data.get('admin_email')  # 호출자가 관리자인지 확인용
    target_email = data.get('email')
    days_to_add = float(data.get('days', 0))

    if not admin_email or not target_email or days_to_add <= 0:
        return jsonify({"result": "fail", "message": "정확한 정보를 입력하세요."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. 관리자 권한 확인
            cursor.execute("SELECT role FROM users WHERE email = %s", (admin_email,))
            admin = cursor.fetchone()
            if not admin or admin['role'] != 'admin':
                return jsonify({"result": "fail", "message": "관리자 권한이 없습니다."}), 403

            # 2. 대상 직원 연차 업데이트 및 권한 부여
            update_sql = """
                UPDATE users 
                SET total_leave = total_leave + %s, role = 'staff' 
                WHERE email = %s
            """
            affected = cursor.execute(update_sql, (days_to_add, target_email))

            if affected == 0:
                return jsonify({"result": "fail", "message": "가입되지 않은 이메일입니다."}), 404

            connection.commit()

        return jsonify({"result": "success", "message": f"{target_email}에 {days_to_add}일 부여 완료."}), 200
    except Exception as e:
        logger.error(f"연차 부여 오류: {str(e)}")
        if connection: connection.rollback()
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()


# ---------------------------
# [엔드포인트] (관리자) 승인 대기열 조회
# ---------------------------
@app.route('/api/admin/leave-queue', methods=['POST'])
def get_leave_queue():
    """관리자 화면에 보여줄 대기 상태의 휴가 신청 목록을 반환합니다."""
    data = request.get_json()
    admin_email = data.get('admin_email')

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 관리자 확인
            cursor.execute("SELECT role FROM users WHERE email = %s", (admin_email,))
            admin = cursor.fetchone()
            if not admin or admin['role'] != 'admin':
                return jsonify({"result": "fail", "message": "권한 없음"}), 403

            # JOIN을 통해 유저 이름/이메일과 함께 대기열 조회
            sql = """
                SELECT r.id, u.name as user_name, u.email as user_email, 
                       r.leave_type, r.start_date, r.end_date, r.reason
                FROM leave_requests r
                JOIN users u ON r.user_id = u.id
                WHERE r.status = '대기'
                ORDER BY r.created_at ASC
            """
            cursor.execute(sql)
            queue = cursor.fetchall()

            # 날짜 형식을 문자열로 변환 (JSON 직렬화 에러 방지)
            for q in queue:
                q['start_date'] = q['start_date'].strftime('%Y-%m-%d')
                q['end_date'] = q['end_date'].strftime('%Y-%m-%d')

        return jsonify({"result": "success", "queue": queue}), 200
    except Exception as e:
        logger.error(f"대기열 조회 오류: {str(e)}")
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()


# ---------------------------
# [엔드포인트] (관리자) 휴가 승인/반려 처리
# ---------------------------
@app.route('/api/admin/process-leave', methods=['POST'])
def process_leave():
    """휴가 신청을 승인/반려 처리하고, 승인 시 사용자의 연차를 차감합니다."""
    data = request.get_json()
    admin_email = data.get('admin_email')
    request_id = data.get('request_id')
    status = data.get('status')  # '승인' 또는 '반려'

    if status not in ['승인', '반려']:
        return jsonify({"result": "fail", "message": "잘못된 상태 값"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. 관리자 권한 확인
            cursor.execute("SELECT role FROM users WHERE email = %s", (admin_email,))
            admin = cursor.fetchone()
            if not admin or admin['role'] != 'admin':
                return jsonify({"result": "fail", "message": "권한 없음"}), 403

            # 2. 신청 내역 조회 및 상태 변경
            cursor.execute("SELECT user_id, deduction_days, status FROM leave_requests WHERE id = %s", (request_id,))
            req = cursor.fetchone()

            if not req or req['status'] != '대기':
                return jsonify({"result": "fail", "message": "유효하지 않거나 이미 처리된 요청입니다."}), 400

            cursor.execute("UPDATE leave_requests SET status = %s WHERE id = %s", (status, request_id))

            # 3. 승인일 경우 연차 차감 진행
            if status == '승인' and req['deduction_days'] > 0:
                cursor.execute("""
                    UPDATE users 
                    SET used_leave = used_leave + %s 
                    WHERE id = %s
                """, (req['deduction_days'], req['user_id']))

            connection.commit()

        return jsonify({"result": "success", "message": f"{status} 처리 완료"}), 200
    except Exception as e:
        logger.error(f"휴가 처리 오류: {str(e)}")
        if connection: connection.rollback()
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()

# ---------------------------
# [엔드포인트] (관리자) 연차 부여를 위한 직원 목록 조회
# ---------------------------
@app.route('/api/admin/staff-list', methods=['GET'])
def get_staff_list():
    """@rootlabs.co.kr 도메인을 가진 직원/일반 사용자 목록을 반환합니다."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 관리자를 제외하고, 루트랩스 메일을 쓰는 user나 staff만 불러옵니다.
            sql = """
                SELECT email, name, role 
                FROM users 
                WHERE role != 'admin' AND email LIKE '%@rootlabs.co.kr'
            """
            cursor.execute(sql)
            staff_list = cursor.fetchall()

        return jsonify({"result": "success", "staff_list": staff_list}), 200
    except Exception as e:
        logger.error(f"직원 목록 조회 오류: {str(e)}")
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()


# ---------------------------
# [엔드포인트] (관리자) 직원별 연차 현황 조회
# ---------------------------
@app.route('/api/admin/staff-balances', methods=['POST'])
def get_staff_balances():
    data = request.get_json()
    admin_email = data.get('admin_email')

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 관리자 확인
            cursor.execute("SELECT role FROM users WHERE email = %s", (admin_email,))
            admin = cursor.fetchone()
            if not admin or admin['role'] != 'admin':
                return jsonify({"result": "fail", "message": "권한 없음"}), 403

            # 직원들 현황 조회
            sql = """
                SELECT name, email, total_leave, used_leave, (total_leave - used_leave) as remain_leave
                FROM users 
                WHERE role = 'staff'
                ORDER BY name ASC
            """
            cursor.execute(sql)
            balances = cursor.fetchall()

        return jsonify({"result": "success", "balances": balances}), 200
    except Exception as e:
        logger.error(f"직원 현황 조회 오류: {str(e)}")
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()


# ---------------------------
# [엔드포인트] (공통) 승인된 캘린더 일정 조회
# ---------------------------
@app.route('/api/leave/calendar', methods=['GET'])
def get_leave_calendar():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 상태가 '승인'인 내역만 가져옵니다.
            sql = """
                SELECT u.name, r.leave_type, r.start_date, r.end_date
                FROM leave_requests r
                JOIN users u ON r.user_id = u.id
                WHERE r.status = '승인'
            """
            cursor.execute(sql)
            events = cursor.fetchall()

            # FullCalendar 규격에 맞게 데이터 가공
            calendar_events = []
            for ev in events:
                # FullCalendar는 종료일(end)이 자정(00:00) 기준이라 하루를 더해줘야 캘린더에 꽉 차게 나옵니다.
                end_date_obj = ev['end_date'] + timedelta(days=1)

                color = "#198754" if ev['leave_type'] == '연차' else "#fd7e14" if '반차' in ev['leave_type'] else "#6c757d"

                calendar_events.append({
                    "title": f"{ev['name']} ({ev['leave_type']})",
                    "start": ev['start_date'].strftime('%Y-%m-%d'),
                    "end": end_date_obj.strftime('%Y-%m-%d'),
                    "color": color,
                    "allDay": True
                })

        return jsonify({"result": "success", "events": calendar_events}), 200
    except Exception as e:
        logger.error(f"캘린더 조회 오류: {str(e)}")
        return jsonify({"result": "error", "message": "서버 오류"}), 500
    finally:
        if connection: connection.close()
        
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
