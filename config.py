# ============================================================================
# config.py — Central Configuration File
# ============================================================================
#
# PURPOSE:
#   Yeh file project ki SAARI settings ek jagah rakhti hai.
#   Agar aapko koi bhi setting change karni ho (jaise zoom level,
#   tile size, ya file paths), toh SIRF yeh file edit karo.
#   Kisi aur file ko touch karne ki zaroorat NAHI hai.
#
# HOW IT WORKS:
#   CONFIG ek Python Dictionary hai — yani key-value pairs ka collection.
#   Example: CONFIG["ZOOM"] ka matlab hai "ZOOM ki value do".
#   Har doosri file isko import karke use karti hai.
#
# ============================================================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --------------------------------------------------------------------------
# BASE_DIR: Project ka root folder automatically detect ho jata hai.
# os.path.dirname(__file__) = jis folder mein config.py hai, woh path.
# Iska faida yeh hai ke code kisi bhi computer pe chalega bina path
# change kiye.
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {

    # ======================================================================
    # PDF RENDERING SETTINGS
    # ======================================================================

    # ZOOM: PDF ko kitna enlarge karke image banana hai.
    #   - 1.0 = Normal size (72 DPI) — choti text nahi parh sakte
    #   - 2.0 = Double size (144 DPI) — theek hai simple drawings ke liye
    #   - 4.0 = 4x size (288 DPI) — BEST for EPC/Shop Drawings jahan
    #           choti text (jaise "REV DATE", duct sizes) clearly padhni ho
    #   - 6.0 = Maximum quality, but BAHUT zyada RAM use karega
    #
    # RAPCO jaise complex drawings ke liye 4.0 recommended hai.
    "ZOOM": 4.0,

    # ======================================================================
    # TILING SETTINGS (Image ko chhote pieces mein kaatna)
    # ======================================================================

    # TILE_SIZE: Har ek tile ki width aur height (pixels mein).
    #   - AI models (GPT-4 Vision, Gemini) usually 1024-1536 px handle karte hain
    #   - 1200px ek acha balance hai quality aur speed ke beech
    #   - Agar AI results galat aa rahe hain, isko 1000 ya 1500 try karo
    "TILE_SIZE": 1200,

    # OVERLAP: Do tiles ke beech kitna overlap hoga (pixels mein).
    #   WHY OVERLAP?
    #   Imagine karo ek duct symbol bilkul tile ki edge pe hai —
    #   bina overlap ke, woh symbol kat jaega aur AI usko pehchaan nahi payega.
    #   300px overlap ensure karta hai ke CUT symbol agla tile mein poora dikhega.
    #
    #   - 200 = Minimum safe overlap
    #   - 300 = Recommended for large duct symbols
    #   - 400 = Use karo agar bahut bade symbols hain
    "OVERLAP": 300,

    # ======================================================================
    # LEGEND / TITLE BLOCK SETTINGS
    # ======================================================================

    # LEGEND_WIDTH_PCT: Drawing ki total width ka kitna % legend hai.
    #   EPC drawings mein title block usually RIGHT side pe hota hai.
    #   - 0.15 (15%) = Small title blocks
    #   - 0.20 (20%) = Standard drawings
    #   - 0.22 (22%) = RAPCO style complex drawings (Recommended)
    #   - 0.25 (25%) = Agar legend bahut wide hai
    "LEGEND_WIDTH_PCT": 0.22,

    # ======================================================================
    # FILE PATHS (Automatically calculated from BASE_DIR)
    # ======================================================================

    # INPUT_PATH: Yahan aapki PDF file honi chahiye.
    # Apni PDF ka naam "drawing.pdf" rakh ke data/input_pdf/ mein daalo.
    "INPUT_PATH": os.path.join(BASE_DIR, "data", "input_pdf", "drawing.pdf"),

    # TILE_OUTPUT: Tiles (chhote image pieces) yahan save honge.
    "TILE_OUTPUT": os.path.join(BASE_DIR, "data", "output_tiles"),

    # LEGEND_OUTPUT: Legend/Title block ki crop ki gayi image yahan save hogi.
    "LEGEND_OUTPUT": os.path.join(BASE_DIR, "data", "legends"),

    # LOG_FILE: System ka log file — agar error aaye toh yahan dekho.
    "LOG_FILE": os.path.join(BASE_DIR, "logs", "system.log"),

    # ======================================================================
    # IMAGE QUALITY SETTINGS (Advanced)
    # ======================================================================

    # SAVE_FORMAT: Output images ka format.
    #   "png" = Best quality (lossless), but file size badi
    #   "jpg" = Choti file size, but thoda quality loss
    "SAVE_FORMAT": "png",

    # GRAYSCALE_MODE: Agar True hai toh tiles ko grayscale mein save karega.
    #   Grayscale se AI ko symbols pehchaanne mein asaani hoti hai
    #   aur file size bhi kam hoti hai.
    #   Abhi ke liye False rakhein (color tiles).
    "GRAYSCALE_MODE": False,

    "MIN_TILE_SIZE": 200,

    # ======================================================================
    # GROQ API SETTINGS (Phase 2 — AI Brain)
    # ======================================================================
    #
    # GROQ KYA HAI?
    #   Groq ek AI inference platform hai jo:
    #   - BILKUL FREE hai (generous free tier)
    #   - Pakistan mein bina VPN ke kaam karta hai
    #   - Vision models support karta hai (image dekhna)
    #   - BAHUT FAST hai (Gemini se bhi fast)
    #
    # API KEY KAHAN SE MILEGI?
    #   1. https://console.groq.com pe jaain
    #   2. Account banao (FREE)
    #   3. API Keys → Create API Key
    #   4. .env file mein daalo: GROQ_API_KEY=gsk_your_key_here

    # GROQ_API_KEY: .env file se load hoti hai
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),

    # GROQ_MODEL: Vision capable model ka naam
    #
    #   MODEL COMPARISON (HVAC Engineering ke liye):
    #   ┌──────────────────────────────────────┬────────┬──────────┬─────────────────────┐
    #   │ Model                                │ Size   │ Accuracy │ HVAC Recommendation │
    #   ├──────────────────────────────────────┼────────┼──────────┼─────────────────────┤
    #   │ llama-3.2-90b-vision-preview         │ 90B    │ ⭐⭐⭐⭐⭐ │ ✅ PRODUCTION use   │
    #   │ llama-3.2-11b-vision-preview         │ 11B    │ ⭐⭐⭐    │ ❌ Miss kar sakta   │
    #   │ meta-llama/llama-4-scout-17b-...     │ 17B    │ ⭐⭐⭐⭐  │ ⚠️  Testing only    │
    #   └──────────────────────────────────────┴────────┴──────────┴─────────────────────┘
    #
    #   WHY 90B FOR HVAC?
    #   HVAC drawings mein symbols bohat chote hote hain (SCD circle = ~20px)
    #   Chota model (17B) "VCD" ko "wall junction" samajh sakta hai
    #   90B model ka vision brain bada hai → chote symbols bhi pakad leta hai
    #
    #   GROQ FREE TIER LIMITS:
    #   - llama-3.2-90b: ~14,400 tokens/minute (kaafi hai humare liye)
    #   - Har tile ~1000-2000 tokens use karta hai
    #   - 20 tiles = ~30,000 tokens = 2-3 minute mein ho jaata hai
    "GROQ_MODEL": "llama-3.2-90b-vision-preview",

    # GROQ_FALLBACK_MODEL: Agar 90b rate limit ho jaye toh yeh use karo
    "GROQ_FALLBACK_MODEL": "meta-llama/llama-4-scout-17b-16e-instruct",

    # ======================================================================
    # PHASE 2 — AI RESULTS PATHS
    # ======================================================================

    # AI_RESULTS_DIR: Har tile ka AI analysis result yahan save hoga
    #   Example: tile_y2700_x3600_result.json
    "AI_RESULTS_DIR": os.path.join(BASE_DIR, "data", "ai_results"),

    # TEST_RESPONSES_DIR: Day 9 single tile testing ke responses yahan
    "TEST_RESPONSES_DIR": os.path.join(BASE_DIR, "data", "test_responses"),

    # LEGEND_MAP_PATH: Legend abbreviations ka JSON file
    "LEGEND_MAP_PATH": os.path.join(BASE_DIR, "data", "legend_map.json"),

    # LEGEND_IMAGE_PATH: Legend reference image (Phase 1 se bani thi)
    "LEGEND_IMAGE_PATH": os.path.join(BASE_DIR, "data", "legends", "legend_reference.png"),

    # SYSTEM_PROMPT_PATH: AI ke liye system prompt file
    "SYSTEM_PROMPT_PATH": os.path.join(BASE_DIR, "prompts", "system_prompt.txt"),

    # TILE_MAP_PATH: Tile coordinates ka JSON (Phase 1 — Day 6 se bana tha)
    "TILE_MAP_PATH": os.path.join(BASE_DIR, "data", "output_tiles", "_tile_map.json"),

    # ======================================================================
    # API RATE LIMITING & RETRY SETTINGS
    # ======================================================================

    # API_DELAY_SECONDS: Do API calls ke beech kitna wait karna hai
    #   Google free tier mein rate limits hain — 2 second safe hai
    #   Agar "429 Too Many Requests" error aaye toh isko 3-5 karo
    "API_DELAY_SECONDS": 2,

    # MAX_RETRIES: Agar API call fail ho toh kitni baar retry karna hai
    #   3 = Industry standard (1st try + 2 retries)
    "MAX_RETRIES": 3,

    # RETRY_BASE_DELAY: Retry ke beech base delay (seconds mein)
    #   Exponential backoff: 1st retry = 2s, 2nd = 4s, 3rd = 8s
    "RETRY_BASE_DELAY": 5,
    "API_DELAY_SECONDS": 5,

    # ======================================================================
    # SPATIAL REASONING DETECTION (SRD) — AI-Native Settings
    # ======================================================================
    #
    # YEH SECTION Level 3 "Spatial Reasoning Detection" ke liye hai.
    # OpenCV ko BILKUL REPLACE karta hai — pure AI bounding box detection.
    #
    # OLD: OpenCV matchTemplate → 1977 noise hits (FAIL)
    # NEW: AI Spatial Reasoning → ~50 precise hits (SUCCESS)

    # SPATIAL_TILE_SIZE: AI ke liye tile size
    #   1024 optimal hai — AI models isko best handle karte hain
    "SPATIAL_TILE_SIZE": 1024,

    # SPATIAL_OVERLAP_PCT: Tiles ke beech overlap (0.10 = 10%)
    #   10% kaafi hai — symbol boundary pe cut nahi hoga
    "SPATIAL_OVERLAP_PCT": 0.10,

    # IOU_THRESHOLD: Deduplication ke liye IoU cutoff
    #   0.30 = 30% overlap → same symbol (duplicate)
    "IOU_THRESHOLD": 0.30,

    # DISTANCE_THRESHOLD: Center distance cutoff for deduplication
    #   80px ke andar agar same code hai → duplicate
    "DISTANCE_THRESHOLD": 80,

    # SPATIAL_PROMPT_PATH: Spatial detection prompt file
    "SPATIAL_PROMPT_PATH": os.path.join(BASE_DIR, "prompts", "spatial_prompt.txt"),

    # SPATIAL_RESULTS_DIR: Spatial detection results
    "SPATIAL_RESULTS_DIR": os.path.join(BASE_DIR, "data", "spatial_results"),

    # SPATIAL_TILES_DIR: Temporary spatial tiles
    "SPATIAL_TILES_DIR": os.path.join(BASE_DIR, "data", "spatial_tiles"),

    # ======================================================================
    # DEEPSEEK API SETTINGS
    # ======================================================================
    #
    # DEEPSEEK KYA HAI?
    #   DeepSeek ek Chinese AI company hai jo OpenAI-compatible API deti hai.
    #   Iska faida: humare existing base64 + multimodal code mein ZERO change!
    #   Sirf api_key aur base_url badalna hai.
    #
    # MODELS:
    #   deepseek-chat        = Text conversations (fast, cheap)
    #   deepseek-vl2         = Vision model (images + text) ← HVAC ke liye
    #
    # API KEY:
    #   .env file mein pehle se hai: DEEPSEEK_API_KEY=sk-xxxx
    #
    # DEEPSEEK FREE TIER:
    #   New accounts ko $5 free credits milte hain
    #   deepseek-vl2: ~$0.002 per 1000 input tokens (Groq se bhi sasta!)

    # DEEPSEEK_API_KEY: .env file se load hota hai
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),

    # DEEPSEEK_BASE_URL: DeepSeek ka official OpenAI-compatible endpoint
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",

    # DEEPSEEK_VISION_MODEL: Legend + tile scanning ke liye model
    #   deepseek-chat      = Supports text + vision via API (RECOMMENDED)
    #   deepseek-reasoner  = Reasoning model (text only)
    #   NOTE: deepseek-vl2 is a LOCAL model only — API pe available nahi hai!
    "DEEPSEEK_VISION_MODEL": "deepseek-chat",

    # AI_PROVIDER: Konsa AI provider use karna hai?
    #   "groq"      = Groq + Llama (current, free, SUPPORTS VISION)
    #   "deepseek"  = DeepSeek API (OpenAI-compatible, TEXT ONLY, does NOT support vision via API)
    #   "auto"      = Groq try karo, fail hone pe DeepSeek fallback
    "AI_PROVIDER": "groq",
}


# ============================================================================
# VALIDATION: Check karo ke settings sahi hain
# ============================================================================
def validate_config():
    """
    Yeh function config values ko check karta hai ke koi galat value toh nahi.
    Agar galat hai toh program shuru hone se pehle hi error de dega.
    """
    errors = []

    if CONFIG["ZOOM"] < 1.0 or CONFIG["ZOOM"] > 8.0:
        errors.append(f"ZOOM must be between 1.0 and 8.0, got {CONFIG['ZOOM']}")

    if CONFIG["TILE_SIZE"] < 500 or CONFIG["TILE_SIZE"] > 3000:
        errors.append(f"TILE_SIZE must be between 500 and 3000, got {CONFIG['TILE_SIZE']}")

    if CONFIG["OVERLAP"] >= CONFIG["TILE_SIZE"]:
        errors.append(f"OVERLAP ({CONFIG['OVERLAP']}) must be smaller than TILE_SIZE ({CONFIG['TILE_SIZE']})")

    if CONFIG["LEGEND_WIDTH_PCT"] <= 0 or CONFIG["LEGEND_WIDTH_PCT"] >= 1.0:
        errors.append(f"LEGEND_WIDTH_PCT must be between 0 and 1.0, got {CONFIG['LEGEND_WIDTH_PCT']}")

    if errors:
        for e in errors:
            print(f"❌ CONFIG ERROR: {e}")
        raise ValueError("Configuration validation failed. Fix the errors above in config.py")

    print("✅ Configuration validated successfully.")
    return True


# Agar yeh file directly run karo toh config print ho jaegi (testing ke liye)
if __name__ == "__main__":
    print("\n📋 Current Configuration:")
    print("=" * 50)
    for key, value in CONFIG.items():
        print(f"  {key:20s} = {value}")
    print("=" * 50)
    validate_config()
