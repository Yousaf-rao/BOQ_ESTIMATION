# ============================================================================
# deepseek_client.py — DeepSeek AI Vision Client (OpenAI-Compatible API)
# ============================================================================
#
# 🎯 YEH FILE KYA KARTI HAI?
#   DeepSeek AI se HVAC symbols detect karna — Groq ka ek smart alternative.
#
# DEEPSEEK KYUN?
#   ✅ OpenAI-compatible API (same format, zero new learning)
#   ✅ deepseek-vl2 = Diagram understanding mein specialist
#   ✅ Layout + spatial relationships samajhta hai (HVAC legend ke liye perfect)
#   ✅ $0.002 / 1000 tokens (Groq free tier se bhi sasta)
#   ✅ Pakistan mein kaam karta hai (API access)
#
# GROQ VS DEEPSEEK:
#   Groq   → Fast, Free tier, but vision models limited hain
#   DeepSeek → Better diagram understanding, paid but very cheap
#
# SAME INTERFACE:
#   Yeh class GeminiHVACClient jaisi hi interface deti hai.
#   Matlab spatial_detector.py, phase2_brain_engine.py mein
#   KOI CHANGE NAHI karna parega.
#
# 📝 HOW TO RUN (Legend Test):
#     python deepseek_client.py
#
# 🔗 DEPENDS ON:
#     - config.py (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, etc.)
#     - .env file (DEEPSEEK_API_KEY=sk-xxxx)
#     - openai Python package: pip install openai
#
# ============================================================================

import os
import sys
import json
import time
import logging
import re
import base64
import io

# OpenAI library — DeepSeek uses same format!
# Install: pip install openai
from openai import OpenAI

from config import CONFIG

# Logging
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class DeepSeekHVACClient:
    """
    DeepSeek AI se baat karne wala HVAC Vision Client.

    SAME INTERFACE as GeminiHVACClient:
        - analyze_tile(tile_path, legend_path) → dict
        - analyze_tile_spatial(tile_path, legend_path) → dict
        - extract_and_update_legend(legend_path) → bool

    HOW IT WORKS (Internally):
        1. OpenAI() client banao with DeepSeek base URL
        2. Image → base64 convert karo (same as Groq)
        3. deepseek-vl2 model ko multimodal request bhejo
        4. JSON response parse karo (same 3-layer parsing)
    """

    def __init__(self):
        """Client initialize: API key check, client banao, model confirm karo."""

        print("\n  🤖 Initializing HVAC Vision Client (DeepSeek VL2)...")

        # ------------------------------------------------------------------
        # STEP 1: API Key Check
        # ------------------------------------------------------------------
        self.api_key = CONFIG.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            print("  ❌ DEEPSEEK_API_KEY not found in .env!")
            print("")
            print("  📝 Yeh karo:")
            print("     1. https://platform.deepseek.com pe jaain")
            print("     2. Account banao (pehle $5 free credits milte hain)")
            print("     3. API Key banao")
            print("     4. .env file mein likho:  DEEPSEEK_API_KEY=sk-xxxx")
            raise ValueError("DEEPSEEK_API_KEY missing. Get key from platform.deepseek.com")

        # ------------------------------------------------------------------
        # STEP 2: OpenAI Client (DeepSeek endpoint ke saath)
        # ------------------------------------------------------------------
        # DeepSeek ka API format bilkul OpenAI jaisa hai!
        # Bas base_url alag hai → api.deepseek.com/v1
        self.base_url = CONFIG.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        print(f"  ✅ DeepSeek client ready (key: ...{self.api_key[-6:]})")
        print(f"  ✅ Endpoint: {self.base_url}")

        # ------------------------------------------------------------------
        # STEP 3: Model Setup
        # ------------------------------------------------------------------
        # deepseek-vl2 = Vision-Language Model v2
        # - Engineering diagrams mein specialist
        # - Layout + spatial relationships samajhta hai
        # - HVAC legend ke liye perfect
        self.model_name    = CONFIG.get("DEEPSEEK_VISION_MODEL", "deepseek-vl2")
        self.fallback_model = "deepseek-chat"   # Text fallback (vision fail pe)
        print(f"  ✅ Vision model : {self.model_name}")

        # ------------------------------------------------------------------
        # STEP 4: Load System Prompt
        # ------------------------------------------------------------------
        self.system_prompt = self._load_system_prompt()
        print(f"  ✅ System prompt loaded ({len(self.system_prompt)} chars)")

        # ------------------------------------------------------------------
        # STEP 5: Load Legend Map
        # ------------------------------------------------------------------
        self.legend_map = self._load_legend_map()
        print(f"  ✅ Legend map loaded ({len(self.legend_map)} symbols)")

        # ------------------------------------------------------------------
        # Settings
        # ------------------------------------------------------------------
        self.max_retries      = CONFIG.get("MAX_RETRIES", 3)
        self.retry_base_delay = CONFIG.get("RETRY_BASE_DELAY", 5)

        # Stats
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens": 0,
            "total_time_seconds": 0,
        }

        logging.info(f"DeepSeekClient initialized: model={self.model_name}")
        print("  🤖 DeepSeek HVAC Client ready!\n")

    # ======================================================================
    # PUBLIC METHODS (same interface as GeminiHVACClient)
    # ======================================================================

    def analyze_tile(self, tile_path, legend_path):
        """
        Tile analyze karo — HVAC symbols count karo.

        Parameters:
            tile_path   : Floor plan tile ka path
            legend_path : Legend reference image ka path

        Returns:
            dict: Structured JSON response with symbol counts
            None: Agar fail ho
        """
        tile_filename = os.path.basename(tile_path)
        print(f"  🔍 [DeepSeek] Analyzing: {tile_filename}")

        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=1000)
            tile_b64   = self._image_to_base64(tile_path,   max_size=1000)
        except FileNotFoundError as e:
            print(f"  ❌ Image not found: {e}")
            return None

        prompt_text = self._build_prompt(tile_filename)

        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {
                            "role": "user",
                            "content": [
                                # Legend image
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{legend_b64}"
                                    }
                                },
                                {"type": "text", "text": "This is the REFERENCE LEGEND showing HVAC symbols."},
                                # Tile image
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{tile_b64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "This is the FLOOR PLAN TILE. "
                                        "Using the legend above as reference, "
                                        "identify and count all HVAC symbols visible in this tile. "
                                        "Return ONLY raw JSON matching the schema provided."
                                    )
                                },
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )

                elapsed = time.time() - start_time
                self.stats["total_calls"] += 1
                self.stats["total_time_seconds"] += elapsed

                raw_text = response.choices[0].message.content
                parsed   = self._parse_json_response(raw_text)

                if parsed is not None:
                    self.stats["successful_calls"] += 1
                    try:
                        tokens = response.usage.total_tokens
                        self.stats["total_tokens"] += tokens
                        print(f"     ⏱️  {elapsed:.1f}s | Tokens: {tokens}")
                    except Exception:
                        print(f"     ⏱️  {elapsed:.1f}s")
                    logging.info(f"✅ DeepSeek success: {tile_filename} | {elapsed:.1f}s")
                    return parsed
                else:
                    print(f"     ⚠️  Invalid JSON on attempt {attempt}")

            except Exception as e:
                error_msg = str(e)
                print(f"     ❌ Attempt {attempt}/{self.max_retries}: {error_msg[:80]}")
                logging.error(f"DeepSeek error: {tile_filename}: {error_msg}")

                wait_time = self.retry_base_delay * (2 ** attempt)
                if "429" in error_msg or "rate" in error_msg.lower():
                    print(f"     ⏳ Rate limit! Waiting {wait_time}s...")
                elif attempt < self.max_retries:
                    print(f"     ⏳ Retrying in {wait_time}s...")

                if attempt < self.max_retries:
                    time.sleep(wait_time)

        self.stats["failed_calls"] += 1
        return None

    def analyze_tile_spatial(self, tile_path, legend_path, spatial_prompt=None):
        """
        SPATIAL MODE: Tile analyze karke bounding boxes return karo.

        Parameters:
            tile_path     : Floor plan tile ka path
            legend_path   : Legend reference image ka path
            spatial_prompt: Custom prompt (optional)

        Returns:
            dict: {"detections": [{"label": "SCD", "box_2d": [y,x,y,x]}, ...]}
        """
        tile_filename = os.path.basename(tile_path)
        print(f"  🔍 [DeepSeek Spatial] Analyzing: {tile_filename}")

        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=800)
            tile_b64   = self._image_to_base64(tile_path,   max_size=1024)
        except FileNotFoundError as e:
            print(f"  ❌ Image not found: {e}")
            return {"detections": []}

        # Load spatial prompt
        if spatial_prompt is None:
            prompt_path = CONFIG.get(
                "SPATIAL_PROMPT_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "prompts", "spatial_prompt.txt")
            )
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    spatial_prompt = f.read()
            else:
                spatial_prompt = (
                    "Detect HVAC symbols. Return JSON with 'detections' array "
                    "containing 'label' and 'box_2d' [ymin,xmin,ymax,xmax] 0-1000 scale."
                )

        prompt_text = spatial_prompt.replace("{{TILE_FILENAME}}", tile_filename)

        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{legend_b64}"
                                    }
                                },
                                {"type": "text", "text": "REFERENCE LEGEND (HVAC symbols)."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{tile_b64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "FLOOR PLAN TILE. Detect symbols, return bounding boxes "
                                        "[ymin,xmin,ymax,xmax] in 0-1000 range. Pure JSON only."
                                    )
                                },
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )

                elapsed = time.time() - start_time
                self.stats["total_calls"] += 1
                self.stats["total_time_seconds"] += elapsed

                raw_text = response.choices[0].message.content
                parsed   = self._parse_json_response(raw_text)

                if parsed is not None:
                    self.stats["successful_calls"] += 1
                    try:
                        tokens = response.usage.total_tokens
                        self.stats["total_tokens"] += tokens
                    except Exception:
                        pass
                    return parsed

            except Exception as e:
                error_msg = str(e)
                print(f"     ❌ Attempt {attempt}: {error_msg[:80]}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_base_delay * (2 ** attempt))

        self.stats["failed_calls"] += 1
        return {"detections": []}

    def extract_and_update_legend(self, legend_path=None):
        """
        ★ DEEPSEEK SPECIALIST FEATURE ★
        Legend image scan karke structured JSON extract karo.

        DeepSeek-VL2 diagram understanding mein specialist hai:
        - Multi-column layouts samajhta hai
        - Symbol ↔ Label relationships identify karta hai
        - Directly JSON output deta hai

        Parameters:
            legend_path: Legend image ka path (None = config se)

        Returns:
            bool: True agar successful, False agar fail
        """
        if legend_path is None:
            legend_path = CONFIG["LEGEND_IMAGE_PATH"]

        print(f"\n  🏆 [DeepSeek] Specialist Legend Extraction: {os.path.basename(legend_path)}")
        logging.info("Starting DeepSeek legend extraction")

        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=1200)
        except FileNotFoundError:
            print(f"  ❌ Legend image not found at {legend_path}")
            return False

        # Specialized DeepSeek prompt for legend understanding
        # DeepSeek-VL2 is a document understanding model — yeh prompt
        # uski strengths specifically use karta hai
        legend_prompt = (
            "You are an expert HVAC engineer analyzing an engineering drawing's LEGEND panel.\n\n"
            "Your task:\n"
            "1. Carefully examine EVERY row/entry in this legend.\n"
            "2. Each entry has: [symbol drawing] [ACRONYM] [full description]\n"
            "3. Extract ALL unique acronyms and their full descriptions.\n\n"
            "CRITICAL RULES:\n"
            "- Return ONLY a flat JSON dictionary\n"
            "- Keys = Acronym/Code (uppercase, e.g. 'SCD', 'VAV', 'VD', 'FSD')\n"
            "- Values = Full Description (uppercase, e.g. 'SUPPLY CEILING DIFFUSER')\n"
            "- No explanations, no markdown, no extra text — ONLY the JSON object\n\n"
            "Example correct output:\n"
            "{\"SCD\": \"SUPPLY CEILING DIFFUSER\", \"VAV\": \"VARIABLE AIR VOLUME BOX\", "
            "\"VD\": \"VOLUME DAMPER\", \"FSD\": \"FIRE SMOKE DAMPER\"}"
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"     ⏳ DeepSeek-VL2 analyzing legend (Attempt {attempt})...")

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{legend_b64}"
                                    }
                                },
                                {"type": "text", "text": legend_prompt},
                            ]
                        }
                    ],
                    temperature=0.0,   # Zero temperature = maximum consistency
                    max_tokens=2048,
                )

                raw_text       = response.choices[0].message.content
                extracted_data = self._parse_json_response(raw_text)

                if extracted_data and isinstance(extracted_data, dict):
                    current_map = self._load_legend_map()
                    added_count = 0

                    for key, value in extracted_data.items():
                        k = str(key).strip().upper()
                        v = str(value).strip().upper()
                        if k not in current_map and 1 < len(k) < 20:
                            current_map[k] = v
                            added_count += 1
                            print(f"     ✨ New Symbol: {k} → {v}")

                    if added_count > 0:
                        path = CONFIG["LEGEND_MAP_PATH"]
                        with open(path, 'w', encoding='utf-8') as f:
                            json.dump(current_map, f, indent=2, ensure_ascii=False)
                        self.legend_map = current_map
                        print(f"  ✅ legend_map.json updated with {added_count} new entries!")
                        try:
                            tokens = response.usage.total_tokens
                            print(f"     Tokens used: {tokens}")
                        except Exception:
                            pass
                    else:
                        print(f"  ✅ No new symbols — all already in legend_map.json")

                    return True
                else:
                    print(f"     ⚠️  Invalid JSON received on attempt {attempt}. Retrying...")

            except Exception as e:
                print(f"     ❌ Attempt {attempt} failed: {str(e)[:80]}")
                time.sleep(5)

        print("  ❌ DeepSeek legend extraction failed after all attempts.")
        return False

    def get_stats(self):
        """API usage stats return karo."""
        return self.stats.copy()

    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================

    def _image_to_base64(self, image_path, max_size=1000):
        """Image file ko base64 string mein convert karo (with auto-resize)."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        from PIL import Image as PILImage
        img = PILImage.open(image_path)

        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), PILImage.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')

    def _load_system_prompt(self):
        """System prompt load karo — agar na mile to safe default use karo."""
        path = CONFIG.get("SYSTEM_PROMPT_PATH", "")
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    return content
        # Safe default — no crash, no hang
        return (
            "You are a senior HVAC engineer. Analyze the floor plan tile carefully. "
            "Count all HVAC symbols visible. Return structured JSON only. "
            "Tile file: {{TILE_FILENAME}}"
        )

    def _load_legend_map(self):
        """Legend map JSON load karo — agar na mile to empty dict return karo."""
        path = CONFIG.get("LEGEND_MAP_PATH", "")
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}  # Safe empty default

    def _build_prompt(self, tile_filename):
        """System prompt mein tile filename inject karo."""
        return self.system_prompt.replace("{{TILE_FILENAME}}", tile_filename)

    def _parse_json_response(self, raw_text):
        """
        AI response → JSON dict.
        3-layer parsing (same as GeminiHVACClient):
            Layer 1: Direct json.loads()
            Layer 2: Markdown fences hataao
            Layer 3: { } brace matching
        """
        if not raw_text or not raw_text.strip():
            return None

        cleaned = raw_text.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        no_fences = re.sub(r'```(?:json)?\s*', '', cleaned).strip()
        try:
            return json.loads(no_fences)
        except json.JSONDecodeError:
            pass

        first = cleaned.find('{')
        last  = cleaned.rfind('}')
        if first != -1 and last > first:
            try:
                return json.loads(cleaned[first:last + 1])
            except json.JSONDecodeError:
                pass

        logging.error(f"DeepSeek JSON parse failed. Sample: {cleaned[:200]}")
        return None


# ============================================================================
# CLIENT FACTORY — AI_PROVIDER ke hisaab se client banao
# ============================================================================
def get_ai_client():
    """
    config.py mein AI_PROVIDER setting ke hisaab se correct client return karo.

    "groq"     → GeminiHVACClient (Groq + Llama)
    "deepseek" → DeepSeekHVACClient (DeepSeek VL2)
    "auto"     → Groq try karo, fail pe DeepSeek use karo

    Returns:
        AI Client object (same interface, either Groq or DeepSeek)
    """
    provider = CONFIG.get("AI_PROVIDER", "auto").lower()

    if provider == "deepseek":
        print("  🧠 Provider: DeepSeek VL2 (forced)")
        return DeepSeekHVACClient()

    elif provider == "groq":
        print("  🧠 Provider: Groq + Llama (forced)")
        from gemini_client import GeminiHVACClient
        return GeminiHVACClient()

    else:  # "auto"
        print("  🧠 Provider: AUTO (Groq first, DeepSeek fallback)")
        try:
            from gemini_client import GeminiHVACClient
            client = GeminiHVACClient()
            print("  ✅ Using Groq (auto-selected)")
            return client
        except Exception as groq_err:
            print(f"  ⚠️  Groq failed ({str(groq_err)[:60]})")
            print("  🔄 Falling back to DeepSeek...")
            return DeepSeekHVACClient()


# ============================================================================
# MAIN TEST — Legend Extraction Test
# ============================================================================
if __name__ == "__main__":

    print("=" * 60)
    print("  🚀 DEEPSEEK VL2 — LEGEND EXTRACTION TEST")
    print("=" * 60)

    try:
        client = DeepSeekHVACClient()
    except ValueError as e:
        print(f"\n  ❌ {e}")
        sys.exit(1)

    legend_path = CONFIG["LEGEND_IMAGE_PATH"]

    if not os.path.exists(legend_path):
        print(f"  ❌ Legend image not found: {legend_path}")
        print(f"  👉 Run day4_legend_extractor.py first")
        sys.exit(1)

    print(f"\n  📋 Legend image: {os.path.basename(legend_path)}")
    print(f"  🤖 Model: {client.model_name}")
    print(f"  {'─' * 50}")
    print(f"\n  ⏳ Sending to DeepSeek VL2 for analysis...")

    success = client.extract_and_update_legend(legend_path)

    if success:
        print(f"\n  ✅ SUCCESS!")
        print(f"  📁 legend_map.json updated: {CONFIG['LEGEND_MAP_PATH']}")
        print(f"\n  📊 Stats: {client.get_stats()}")
    else:
        print(f"\n  ❌ FAILED — Check logs/system.log for details")
