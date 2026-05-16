from flask import Flask, request, render_template, send_file, jsonify, session, redirect, url_for, send_from_directory
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageStat
from io import BytesIO
import os
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
import hashlib
import re
import logging
import threading
from supabase import create_client, Client
from gradio_client import Client as GradioClient, handle_file
import tempfile
from werkzeug.exceptions import HTTPException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from tokens import ACCESS_TOKENS, TRIAL_CODES_ACTIVE, is_trial_token

# ---- Security Logging (stdout only for Serverless) ----
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)
# On Vercel, logs from StreamHandler (stdout/stderr) are automatically captured
security_logger.addHandler(logging.StreamHandler())


class ProcessingError(Exception):
    def __init__(self, code, message, status=500):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

def log_security_event(event_type, details):
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', 'unknown')
    msg = f"[{event_type}] IP: {ip} | UA: {ua} | Details: {details}"
    security_logger.warning(msg)

def get_session_fingerprint():
    """Create a hash of mostly IP prefix to bind the session, with UA as optional salt."""
    # Relaxed fingerprinting: UA can sometimes change in embedded browsers/webviews.
    # We'll use the IP prefix and a simplified UA check if possible.
    ip_parts = str(request.remote_addr).split('.')
    ip_prefix = ".".join(ip_parts[:2]) if len(ip_parts) >= 2 else "unknown"
    fingerprint_raw = f"{ip_prefix}" # Only bind to IP prefix for maximum compatibility
    return hashlib.sha256(fingerprint_raw.encode()).hexdigest()

# Configuration from environment variables
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_SPACE_ID = os.getenv("HF_SPACE_ID")
HF_SPACE_URL = os.getenv("HF_SPACE_URL")
HF_API_NAME = os.getenv("HF_API_NAME", "/remove_bg")

# Initialize HF Client lazily so cold starts do not fail before a request.
hf_client = None
hf_client_lock = threading.Lock()


def get_hf_client():
    global hf_client
    if hf_client:
        return hf_client

    hf_source = HF_SPACE_URL or HF_SPACE_ID
    if not hf_source:
        raise RuntimeError("HF_SPACE_ID or HF_SPACE_URL is not configured")

    with hf_client_lock:
        if hf_client:
            return hf_client
        logger.info("Connecting to HF Space: %s", hf_source)
        hf_client = GradioClient(
            hf_source,
            token=HF_API_TOKEN,
            verbose=False,
            httpx_kwargs={"timeout": 25},
        )
        return hf_client


if HF_SPACE_ID or HF_SPACE_URL:
    try:
        get_hf_client()
    except Exception as e:
        logger.error("Failed to connect to Hugging Face. Will retry during processing: %s", e)


def run_hf_background_removal(image_path: str):
    """
    Call HF Space endpoint with resilient api_name fallback.
    Supports endpoint drift across Space versions.
    """
    api_candidates = []
    if HF_API_NAME:
        api_candidates.append(HF_API_NAME)
    for candidate in ("/remove_bg", "/predict", None):
        if candidate not in api_candidates:
            api_candidates.append(candidate)

    last_error = None
    client = get_hf_client()
    for api_name in api_candidates:
        try:
            if api_name:
                return client.predict(img=handle_file(image_path), api_name=api_name)
            return client.predict(img=handle_file(image_path))
        except Exception as e:
            last_error = e
            err = str(e).lower()
            # If endpoint name is invalid, continue to fallback candidates.
            if "cannot find a function with `api_name`" in err:
                logger.warning("HF endpoint not found: %s", api_name)
                continue
            # Non-endpoint errors are real runtime failures; stop here.
            raise

    raise last_error if last_error else RuntimeError("HF prediction failed")


def read_hf_result(result) -> bytes:
    """Normalize common gradio_client file return shapes into bytes."""
    if isinstance(result, (list, tuple)):
        result = result[0] if result else None
    if isinstance(result, dict):
        result = result.get("path") or result.get("name") or result.get("url")
    if not result:
        raise RuntimeError("HF Space returned an empty result")

    result = str(result)
    if result.startswith(("http://", "https://")):
        response = requests.get(result, timeout=25)
        response.raise_for_status()
        return response.content

    with open(result, "rb") as f:
        return f.read()

# Strict check for required production keys
if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]) or not (HF_SPACE_ID or HF_SPACE_URL):
    logger.error("Missing critical environment variables (Cloudinary or Hugging Face config)")

if not FLASK_SECRET_KEY:
    logger.warning("FLASK_SECRET_KEY not set. Using a fallback, but this is insecure for production.")
    FLASK_SECRET_KEY = "insecure-fallback-key"

# ---- Token Persistence (Supabase) ----
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")

def token_valid(token: str) -> bool:
    if token == "SNAP-DEV-TEST":
        return True
    if not token or token not in ACCESS_TOKENS:
        return False

    # Check if used in database. Active trial codes are renewable, so old
    # used-token rows should not block them.
    if supabase and not (TRIAL_CODES_ACTIVE and is_trial_token(token)):
        try:
            result = supabase.table("used_tokens").select("token").eq("token", token).execute()
            if result.data:
                return False
        except Exception as e:
            logger.error(f"Database error during token validation: {e}")
            # Fail closed for security
            return False
            
    expiry = ACCESS_TOKENS[token]
    if expiry is None:
        return True
    return datetime.now(timezone.utc) < expiry


def access_badge_for_token(token: str):
    expiry = ACCESS_TOKENS.get(token)
    if is_trial_token(token):
        return {
            "type": "trial",
            "label": "3 Day Trial",
            "expiresAt": expiry.isoformat() if expiry else None,
        }
    if expiry is None:
        return {
            "type": "lifetime",
            "label": "Special Lifetime",
            "expiresAt": None,
        }
    return None

def consume_token(token: str):
    """Mark token as used. SNAP-DEV-TEST is exempt."""
    if token == "SNAP-DEV-TEST":
        return
    if TRIAL_CODES_ACTIVE and is_trial_token(token):
        return
    if token in ACCESS_TOKENS:
        if supabase:
            try:
                supabase.table("used_tokens").insert({"token": token}).execute()
            except Exception as e:
                logger.error(f"Failed to consume token in database: {e}")


def token_consumed(token: str) -> bool:
    if token == "SNAP-DEV-TEST":
        return False
    if not supabase:
        return False
    try:
        result = supabase.table("used_tokens").select("token").eq("token", token).execute()
        return bool(result.data)
    except Exception as e:
        logger.error(f"Database error while checking consumed token: {e}")
        return False

# ---- Smart Enhancement Presets ----
ENHANCE_PRESETS = {
    "dark": [
        # Controlled brightening for underexposed / low-light shots
        {"effect": "auto_color"},
        {"effect": "auto_brightness"},
        {"effect": "brightness:14"},
        {"effect": "gamma:-12"},
        {"effect": "fill_light:16"},
        {"effect": "contrast:8"},
        {"effect": "improve:35"},
        {"effect": "sharpen:35"},
    ],
    "warm": [
        # Cool down yellow/orange cast, restore neutral skin tones
        {"effect": "auto_color"},
        {"effect": "improve:32"},
        {"effect": "saturation:-8"},
        {"effect": "brightness:8"},
        {"effect": "fill_light:10"},
        {"effect": "contrast:6"},
        {"effect": "sharpen:28"},
    ],
    "normal": [
        # Natural enhancement for well-lit photos
        {"effect": "auto_color"},
        {"effect": "auto_brightness"},
        {"effect": "improve:30"},
        {"effect": "brightness:6"},
        {"effect": "gamma:-6"},
        {"effect": "fill_light:8"},
        {"effect": "contrast:5"},
        {"effect": "sharpen:22"},
    ],
}

CAMERA_ENHANCE_PRESETS = {
    "dark": [
        {"effect": "auto_color"},
        {"effect": "brightness:2"},
        {"effect": "gamma:-3"},
        {"effect": "fill_light:4"},
        {"effect": "contrast:5"},
        {"effect": "saturation:4"},
        {"effect": "improve:14"},
        {"effect": "sharpen:10"},
    ],
    "warm": [
        {"effect": "auto_color"},
        {"effect": "saturation:-5"},
        {"effect": "brightness:1"},
        {"effect": "fill_light:3"},
        {"effect": "contrast:5"},
        {"effect": "improve:14"},
        {"effect": "sharpen:10"},
    ],
    "normal": [
        {"effect": "auto_color"},
        {"effect": "brightness:0"},
        {"effect": "fill_light:2"},
        {"effect": "contrast:4"},
        {"effect": "saturation:3"},
        {"effect": "improve:12"},
        {"effect": "sharpen:8"},
    ],
}


def estimate_sharpness_score(img_rgb: Image.Image) -> float:
    """
    Lightweight sharpness estimate:
    higher score => stronger edges (less blur).
    """
    sample = img_rgb.convert("L").resize((220, 220), Image.Resampling.BILINEAR)
    edges = sample.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    return float(stat.mean[0])


def refine_portrait_quality(img: Image.Image, mode: str, source_type: str = "upload") -> Image.Image:
    """
    Local post-enhancement pass to reduce blur/pixelation artifacts:
    - smart upscale for low-res inputs
    - mild denoise
    - autocontrast + unsharp + detail
    """
    has_alpha = img.mode == "RGBA"
    alpha = img.split()[-1] if has_alpha else None
    rgb = img.convert("RGB")

    # Upscale only very low-res sources to reduce blocky appearance.
    w, h = rgb.size
    min_side = min(w, h)
    if min_side < 520:
        scale = 1.35
    elif min_side < 760:
        scale = 1.15
    else:
        scale = 1.0
    if scale > 1.0:
        rgb = rgb.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    sharpness_score = estimate_sharpness_score(rgb)

    # Very mild cleanup before sharpening to avoid halos.
    rgb = rgb.filter(ImageFilter.MedianFilter(size=3))
    if source_type == "camera":
        # Autocontrast on webcam captures can wash out skin and flatten dynamic range.
        rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    else:
        rgb = ImageOps.autocontrast(rgb, cutoff=0.4)

    # Mode-aware tonal adjustments.
    if mode == "dark":
        rgb = ImageEnhance.Brightness(rgb).enhance(1.03)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.04)
    elif mode == "warm":
        rgb = ImageEnhance.Contrast(rgb).enhance(1.03)
        rgb = ImageEnhance.Color(rgb).enhance(0.98)
    else:
        rgb = ImageEnhance.Contrast(rgb).enhance(1.02)

    # Camera tone recovery for pale captures after bg removal.
    if source_type == "camera":
        stat = ImageStat.Stat(rgb)
        avg_luma = sum(stat.mean) / 3.0
        if avg_luma > 166:
            rgb = ImageEnhance.Brightness(rgb).enhance(0.94)
            rgb = ImageEnhance.Color(rgb).enhance(1.12)
            rgb = ImageEnhance.Contrast(rgb).enhance(1.07)
        else:
            rgb = ImageEnhance.Color(rgb).enhance(1.06)

    # Keep sharpening conservative to prevent crunchy skin / edge halos.
    if sharpness_score < 18:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.1, percent=100, threshold=3))
    elif sharpness_score < 26:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.9, percent=78, threshold=3))
    else:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.8, percent=58, threshold=4))

    if has_alpha and alpha is not None:
        out = rgb.convert("RGBA")
        out.putalpha(alpha.resize(out.size, Image.Resampling.BILINEAR))
        return out
    return rgb.convert("RGBA")

# ---- Rate Limiting ----
limiter = Limiter(
    get_remote_address,
    app=None,
    default_limits=["200 per day", "100 per hour"],
    storage_uri="memory://",
)

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = FLASK_SECRET_KEY
csrf = CSRFProtect(app)

# Initialize limiter with app
limiter.init_app(app)

# Cloudinary Configuration
cloudinary.config(
  cloud_name = CLOUDINARY_CLOUD_NAME,
  api_key = CLOUDINARY_API_KEY,
  api_secret = CLOUDINARY_API_SECRET,
  secure = True
)

@app.after_request
def add_security_headers(response):
    """Add basic security headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"ok": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return jsonify({"ok": False, "error": "Internal server error. Please try again later."}), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"ok": False, "error": "Too many requests. Please slow down."}), 429


@app.errorhandler(Exception)
def handle_unexpected_exception(error):
    if isinstance(error, HTTPException):
        return error
    logger.exception("Unhandled exception")
    return jsonify({"ok": False, "error": "Internal server error. Please try again later."}), 500

@app.route("/")
def index():
    # Allow unlocking via URL parameter (e.g. /?token=SNAP-XXX)
    token_param = request.args.get("token", "").strip().upper()
    if token_param and token_valid(token_param):
        consume_token(token_param)
        session["authenticated"] = True
        session["fingerprint"] = get_session_fingerprint()
        session["access_badge"] = access_badge_for_token(token_param)
        log_security_event("TOKEN_VALIDATED_URL", f"Token: {token_param}")
        return redirect(url_for("index"))

    authenticated = session.get("authenticated", False)
    return render_template(
        "index.html",
        authenticated=authenticated,
        access_badge=session.get("access_badge") if authenticated else None,
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/guide")
def guide():
    return render_template("guide.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory("assets", "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp

@app.route("/validate-token", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def validate_token():
    # 1. Honeypot check (anti-bot)
    # We use request.form because simple bots fill form fields in a POST
    # even if the request is expected to be JSON.
    # Note: If request is JSON, we'll check the data dict.
    data = request.get_json(silent=True) or request.form.to_dict()
    if data.get("hp_field"):  # Hidden honeypot field
        log_security_event("HONEYPOT_TRIGGERED", "Bot detected via hidden field")
        return jsonify({"ok": False, "error": "security_check_failed"}), 403

    token = str(data.get("token", "")).strip().upper()

    # 2. Regex pre-validation (reduce overhead)
    if not re.match(r"^[A-Z0-9-]{4,32}$", token):
        log_security_event("INVALID_TOKEN_FORMAT", f"Attempted token: {token}")
        return jsonify({"ok": False, "error": "Invalid token format"}), 400

    if token_valid(token):
        consume_token(token)          # mark as used — single-use enforcement
        session["authenticated"] = True
        
        # 3. Session Binding (Anti-Hijacking)
        session["fingerprint"] = get_session_fingerprint()
        
        expiry = ACCESS_TOKENS[token]
        badge = access_badge_for_token(token)
        session["access_badge"] = badge
        log_security_event("TOKEN_VALIDATED", f"Token: {token}")
        return jsonify({
            "ok": True,
            "lifetime": expiry is None,
            "expires": expiry.strftime("%Y-%m-%d") if expiry else None,
            "badge": badge,
        })
    
    if token_consumed(token):
        log_security_event("USED_TOKEN_ATTEMPT", f"Token: {token}")
        return jsonify({"ok": False, "error": "Token already used"}), 401
        
    log_security_event("FAILED_TOKEN_ATTEMPT", f"Token: {token}")
    return jsonify({"ok": False, "error": "Invalid or expired token"}), 401


def detect_image_mode(img_bytes):
    """Analyse pixel stats to pick the right enhancement preset."""
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB").resize((80, 80))
        # Get pixels efficiently without triggering deprecation warnings
        pixels = list(img.getdata())
        r = sum(p[0] for p in pixels) / len(pixels)
        g = sum(p[1] for p in pixels) / len(pixels)
        b = sum(p[2] for p in pixels) / len(pixels)
        brightness = (r + g + b) / (3 * 255)
        warmth = r / (b + 1e-6)   # red-to-blue ratio; high = warm/yellow cast
        if brightness < 0.38:
            return "dark"
        if warmth > 1.28:
            return "warm"
        return "normal"
    except Exception:
        return "normal"


def has_solid_white_background(img_bytes) -> bool:
    """
    Return True when the visible background already matches the white print sheet.

    This intentionally uses a conservative border/corner check. Passport subjects
    usually sit in the center, so a genuinely white backdrop should dominate the
    outer strips and corners with very little color variation.
    """
    try:
        img = Image.open(BytesIO(img_bytes))
        img = ImageOps.exif_transpose(img)

        # If an image is already transparent, it is not a solid white-background
        # source; let the normal pipeline preserve its alpha handling.
        if img.mode in ("RGBA", "LA"):
            alpha = img.getchannel("A")
            if alpha.getextrema()[0] < 250:
                return False

        img = img.convert("RGB")
        img.thumbnail((320, 320), Image.Resampling.BILINEAR)
        width, height = img.size
        if width < 24 or height < 24:
            return False

        strip = max(8, min(24, int(min(width, height) * 0.08)))
        corner = max(strip, min(40, int(min(width, height) * 0.14)))

        border_regions = [
            img.crop((0, 0, width, strip)),
            img.crop((0, height - strip, width, height)),
            img.crop((0, 0, strip, height)),
            img.crop((width - strip, 0, width, height)),
        ]
        corner_regions = [
            img.crop((0, 0, corner, corner)),
            img.crop((width - corner, 0, width, corner)),
            img.crop((0, height - corner, corner, height)),
            img.crop((width - corner, height - corner, width, height)),
        ]

        def white_stats(regions):
            pixels = []
            for region in regions:
                pixels.extend(region.getdata())

            if not pixels:
                return 0.0, 0.0, (0.0, 0.0, 0.0)

            white_count = 0
            luminance_values = []
            channel_sums = [0, 0, 0]
            for r, g, b in pixels:
                channel_sums[0] += r
                channel_sums[1] += g
                channel_sums[2] += b
                luminance = (r + g + b) / 3.0
                luminance_values.append(luminance)
                if r >= 238 and g >= 238 and b >= 238 and (max(r, g, b) - min(r, g, b)) <= 16:
                    white_count += 1

            mean_luma = sum(luminance_values) / len(luminance_values)
            variance = sum((value - mean_luma) ** 2 for value in luminance_values) / len(luminance_values)
            means = tuple(total / len(pixels) for total in channel_sums)
            return white_count / len(pixels), variance ** 0.5, means

        border_white_ratio, border_luma_std, border_means = white_stats(border_regions)
        corner_white_ratio, corner_luma_std, corner_means = white_stats(corner_regions)
        border_region_stats = [white_stats([region]) for region in border_regions]
        corner_region_stats = [white_stats([region]) for region in corner_regions]
        border_mean_min = min(border_means)
        corner_mean_min = min(corner_means)

        return (
            border_white_ratio >= 0.92
            and corner_white_ratio >= 0.96
            and all(stats[0] >= 0.88 for stats in border_region_stats)
            and all(stats[0] >= 0.94 for stats in corner_region_stats)
            and border_luma_std <= 10
            and corner_luma_std <= 8
            and border_mean_min >= 242
            and corner_mean_min >= 245
        )
    except Exception as e:
        logger.warning("White-background detection skipped due to error: %s", e)
        return False


def process_single_image(input_image_bytes, enhance_mode="auto", source_type="upload"):
    """Remove background via Hugging Face Space and enhance via Cloudinary."""

    bg_removed_ok = False
    bg_removed_content = input_image_bytes

    # Step 1: Background removal via Hugging Face Space
    temp_path = None
    if has_solid_white_background(input_image_bytes):
        logger.info("DEBUG: Solid white background detected; skipping background removal for this image")
    else:
        try:
            logger.info("DEBUG: Removing background via Hugging Face Space...")

            # Save bytes to a temporary file because gradio_client works best with files.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(input_image_bytes)
                temp_path = temp_file.name

            result = run_hf_background_removal(temp_path)
            bg_removed_content = read_hf_result(result)
            bg_removed_ok = True
            logger.info("DEBUG: Background removed successfully via Hugging Face")

        except Exception as e:
            err = str(e).lower()
            logger.warning("HF background removal failed: %s", e)
            if "429" in err or "quota" in err or "rate limit" in err:
                raise ProcessingError("quota_exceeded", "AI quota exceeded. Please try again later.", 429)
            if "401" in err or "unauthorized" in err or "invalid user token" in err or "expired" in err:
                raise ProcessingError("hf_auth_failed", "Background removal is not authorized. Please update the Hugging Face token.", 503)
            raise ProcessingError("hf_background_failed", "Background removal service is unavailable. Please try again.", 503)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    logger.warning("Temp file cleanup failed: %s", temp_path)

    # Auto-detect image condition if mode not forced by user
    if enhance_mode == "none":
        detected_mode = "none"
    else:
        detected_mode = enhance_mode if enhance_mode in ENHANCE_PRESETS else detect_image_mode(input_image_bytes)

    if source_type == "camera" and enhance_mode == "auto" and detected_mode == "dark":
        detected_mode = "normal"
    print(f"DEBUG: enhance_mode={enhance_mode}, source_type={source_type}, detected_mode={detected_mode}")

    # Step 2: Photo Enhancement via Cloudinary
    final_content = bg_removed_content
    if detected_mode != "none":
        try:
            print(f"DEBUG: Uploading to Cloudinary — preset: {detected_mode}")
            preset_map = CAMERA_ENHANCE_PRESETS if source_type == "camera" else ENHANCE_PRESETS
            upload_result = cloudinary.uploader.upload(
                bg_removed_content,
                quality="auto:best",
                transformation=preset_map[detected_mode]
            )
            enhanced_url = upload_result.get("secure_url")
            if enhanced_url:
                print(f"DEBUG: Enhanced image URL: {enhanced_url}")
                enhanced_response = requests.get(enhanced_url, timeout=30)
                if enhanced_response.ok:
                    final_content = enhanced_response.content
                else:
                    print(f"WARNING: Failed to download enhanced image: {enhanced_response.status_code}")
            else:
                print("WARNING: Cloudinary did not return a secure_url")
        except Exception as e:
            print(f"ERROR: Cloudinary enhancement failed: {e}")
    else:
        print("DEBUG: Enhancement skipped (mode=none)")

    img = Image.open(BytesIO(final_content))

    # Keep transparency intact — convert to RGBA so alpha channel is preserved
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Final local enhancement pass to reduce blur/pixelation artifacts.
    try:
        refine_mode = "normal" if source_type == "camera" and detected_mode in ("dark", "warm") else detected_mode
        img = refine_portrait_quality(img, refine_mode, source_type=source_type)
    except Exception as e:
        logger.warning("Local quality refinement skipped due to error: %s", e)

    return img, detected_mode, bg_removed_ok


@app.route("/process", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def process():
    if not session.get("authenticated"):
        return jsonify({"error": "unauthorized"}), 401
    
    # Session Binding Check
    if session.get("fingerprint") != get_session_fingerprint():
        log_security_event("SESSION_FINGERPRINT_MISMATCH", "Likely session hijacking attempt")
        session.clear()
        return jsonify({"error": "session_expired"}), 401

    print("==== /process endpoint hit ====")

    def parse_int(name, default, min_value, max_value):
        raw_value = request.form.get(name, default)
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ProcessingError("invalid_input", f"Invalid value for '{name}'.", 400)
        if value < min_value or value > max_value:
            raise ProcessingError("invalid_input", f"'{name}' must be between {min_value} and {max_value}.", 400)
        return value

    # Layout settings
    passport_width = parse_int("width", 390, 100, 4000)
    passport_height = parse_int("height", 480, 100, 5000)
    border = parse_int("border", 2, 0, 200)
    spacing = parse_int("spacing", 10, 0, 800)
    print_dpi = parse_int("print_dpi", 300, 150, 1200)
    dpi_scale = print_dpi / 300.0
    margin_x = max(1, round(10 * dpi_scale))
    margin_y = max(1, round(10 * dpi_scale))
    horizontal_gap = max(0, round(10 * dpi_scale))
    a4_w = round((210 / 25.4) * print_dpi)
    a4_h = round((297 / 25.4) * print_dpi)

    # Collect images and their copy counts
    images_data = []

    i = 0
    while f"image_{i}" in request.files:
        file = request.files[f"image_{i}"]
        copies = parse_int(f"copies_{i}", 6, 1, 54)
        source_type = request.form.get(f"source_{i}", "upload")
        images_data.append((file.read(), copies, source_type))
        i += 1

    # Fallback to single image mode
    if not images_data and "image" in request.files:
        file = request.files["image"]
        copies = parse_int("copies", 6, 1, 54)
        source_type = request.form.get("source", "upload")
        images_data.append((file.read(), copies, source_type))

    if not images_data:
        return jsonify({"ok": False, "code": "no_image_uploaded", "error": "No image uploaded."}), 400

    enhance_mode = request.form.get("enhance_mode", "auto")
    logger.info(f"DEBUG: Processing {len(images_data)} image(s) | enhance_mode={enhance_mode}")
    start_time = time.time()

    # Process all images in parallel
    passport_images = []
    detected_modes = []
    bg_removal_states = []

    def process_wrapper(img_data_item):
        img_bytes, copies, source_type = img_data_item
        img, det_mode, bg_removed_ok = process_single_image(img_bytes, enhance_mode, source_type)
        return img, copies, det_mode, bg_removed_ok

    try:
        with ThreadPoolExecutor(max_workers=min(len(images_data), 10)) as executor:
            results = list(executor.map(process_wrapper, images_data))

        for img, copies, det_mode, bg_removed_ok in results:
            detected_modes.append(det_mode)
            bg_removal_states.append(bg_removed_ok)
            img = img.resize((passport_width, passport_height), Image.LANCZOS)
            img = ImageOps.expand(img, border=border, fill=(0, 0, 0, 255))
            passport_images.append((img, copies))

    except ProcessingError as e:
        logger.warning("Processing error [%s]: %s", e.code, e.message)
        return jsonify({"ok": False, "code": e.code, "error": e.message}), e.status
    except Exception:
        logger.exception("Unexpected processing failure")
        return jsonify({"ok": False, "code": "processing_failed", "error": "Image processing failed. Please try again."}), 500

    print(f"DEBUG: Total processing time: {time.time() - start_time:.2f}s")

    paste_w = passport_width + 2 * border
    paste_h = passport_height + 2 * border

    # Build all pages
    pages = []
    current_page = Image.new("RGB", (a4_w, a4_h), "white")
    x, y = margin_x, margin_y

    def new_page():
        nonlocal current_page, x, y
        pages.append(current_page)
        current_page = Image.new("RGB", (a4_w, a4_h), "white")
        x, y = margin_x, margin_y

    for passport_img, copies in passport_images:
        for _ in range(copies):
            if x + paste_w > a4_w - margin_x:
                x = margin_x
                y += paste_h + spacing

            if y + paste_h > a4_h - margin_y:
                new_page()

            # Use alpha channel as mask so transparent areas show white A4 background
            mask = passport_img.split()[-1] if passport_img.mode == "RGBA" else None
            current_page.paste(passport_img, (x, y), mask=mask)
            print(f"DEBUG: Placed at x={x}, y={y}")
            x += paste_w + horizontal_gap

    pages.append(current_page)
    print(f"DEBUG: Total pages = {len(pages)}")

    # Export multi-page PDF with ReportLab for faster and precise page rendering.
    # Keep the selected print DPI mapping by converting pixel dimensions to PDF points.
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except Exception:
        logger.exception("ReportLab import failed")
        return jsonify({"ok": False, "code": "pdf_engine_unavailable", "error": "PDF engine unavailable. Please install reportlab."}), 500

    output = BytesIO()
    page_w_pt = a4_w * 72.0 / print_dpi
    page_h_pt = a4_h * 72.0 / print_dpi
    pdf = canvas.Canvas(output, pagesize=(page_w_pt, page_h_pt), pageCompression=1)

    for page_img in pages:
        page_buffer = BytesIO()
        page_img.save(page_buffer, format="PNG", optimize=True)
        page_buffer.seek(0)
        pdf.drawImage(
            ImageReader(page_buffer),
            0,
            0,
            width=page_w_pt,
            height=page_h_pt,
            preserveAspectRatio=False,
            mask="auto",
        )
        pdf.showPage()

    pdf.save()
    output.seek(0)
    print("DEBUG: Returning PDF to client")

    resp = send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="passport-sheet.pdf",
    )
    resp.headers["X-Detected-Mode"] = detected_modes[0] if detected_modes else "normal"
    resp.headers["X-BG-Removal"] = "partial" if (bg_removal_states and not all(bg_removal_states)) else "applied"
    resp.headers["X-BG-Removal-States"] = ",".join("applied" if state else "skipped" for state in bg_removal_states)
    resp.headers["X-Print-DPI"] = str(print_dpi)
    resp.headers["Access-Control-Expose-Headers"] = "X-Detected-Mode, X-BG-Removal, X-BG-Removal-States, X-Print-DPI"
    return resp

if __name__ == "__main__":
    # For Windows production, use waitress: pip install waitress
    # run: waitress-serve --port=5000 app:app
    app.run(host="0.0.0.0", port=5000, debug=False)
