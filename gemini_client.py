# ============================================================================
# gemini_client.py — Day 9: HVAC AI Vision Client (Groq + Llama Vision)
# ============================================================================
#
# 🎯 OBJECTIVE: Drawing tiles ko AI se analyze karna!
#   Pehle hum Gemini try karte the, but woh Pakistan mein kaam nahi karta.
#   Ab hum GROQ use kar rahe hain — FREE, FAST, aur Pakistan mein kaam karta hai!
#
# GROQ KYA HAI?
#   Groq ek AI platform hai jahan tum FREE mein powerful AI models use kar sakte ho.
#   Woh Llama (Meta ka open-source AI) run karte hain bahut fast speed pe.
#   Website: https://console.groq.com
#
# GROQ VISION MODEL:
#   "meta-llama/llama-4-scout-17b-16e-instruct" = Latest Llama 4 multimodal model
#   "llama-3.2-90b-vision-preview" = Llama 3.2 vision model (backup)
#   Yeh model TEXT + IMAGES dono samajh sakta hai!
#
# MULTIMODAL KAAM KAISE KARTA HAI:
#   [Legend Image] + [Tile Image] + [System Prompt Text]
#       ↓ (bhejo Groq ko base64 format mein)
#   [Structured JSON Response]
#       ↓ (parse karo)
#   [Python Dictionary] → ready for aggregation
#
# BASE64 KYA HAI?
#   Image file ko direct nahi bhej sakte API ko.
#   Pehle image ko "text format" mein convert karte hain — yahi base64 hai.
#   Example: PNG file → "iVBORw0KGgoAAAANS..." (characters ki long string)
#
# 📝 HOW TO RUN:
#   python gemini_client.py
#
# ZARURI: .env file mein GROQ_API_KEY hona chahiye!
#   1. https://console.groq.com pe jaain
#   2. FREE account banao
#   3. API Key banao
#   4. .env file mein likho: GROQ_API_KEY=gsk_xxxxxxxxxxxx
# ============================================================================

import os
import sys
import json
import time
import logging
import re
import base64  # Image ko text format mein convert karne ke liye

# --------------------------------------------------------------------------
# groq: Groq ka official Python SDK
#   Install: python -m pip install groq
#   Yeh library OpenAI jaisa interface deti hai, but Groq ke servers use karta hai
# --------------------------------------------------------------------------
from groq import Groq

# --------------------------------------------------------------------------
# config.py: Central settings file se saari values import karo
# --------------------------------------------------------------------------
from config import CONFIG

# --------------------------------------------------------------------------
# Logging Setup: Har API call ka record rakhna zaroori hai
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class GeminiHVACClient:
    """
    Groq AI se baat karne wala HVAC Vision Client.
    
    NOTE: Class ka naam "GeminiHVACClient" rakh rahe hain taake
    tile_processor.py, phase2_brain_engine.py mein koi change na karna pade.
    Andar se Groq use ho raha hai, bahar se same interface hai.
    
    YEH CLASS KYA KARTI HAI:
        1. Groq client initialize karta hai (free API)
        2. System prompt load karta hai
        3. Images ko base64 mein convert karta hai (Groq ka format)
        4. Legend + Tile images ke saath Groq ko request bhejta hai
        5. JSON response parse karke return karta hai
    """
    
    def __init__(self):
        """
        Client initialize karo.
        
        STEPS:
            1. GROQ_API_KEY check karo
            2. Groq client object banao
            3. System prompt load karo
            4. Legend map load karo
        """
        
        print("\n  🤖 Initializing HVAC Vision Client (Groq + Llama)...")
        
        # ------------------------------------------------------------------
        # STEP 1: API Key Check
        # ------------------------------------------------------------------
        # GROQ_API_KEY .env file mein honi chahiye
        # Format: GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
        self.api_key = CONFIG["GROQ_API_KEY"]
        
        if not self.api_key:
            print("  ❌ GROQ_API_KEY not found in .env!")
            print("")
            print("  📝 Yeh karo:")
            print("     1. https://console.groq.com pe jaain")
            print("     2. FREE account banao (Google se login ho jata hai)")
            print("     3. Left menu: API Keys → Create API Key")
            print("     4. Key copy karo (gsk_xxxx...)")
            print("     5. .env file mein likho:")
            print("        GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx")
            print("")
            raise ValueError("GROQ_API_KEY missing. Get free key from console.groq.com")
        
        # ------------------------------------------------------------------
        # STEP 2: Groq Client Banao
        # ------------------------------------------------------------------
        # Groq() = Groq ka client object
        # Yeh automatically GROQ_API_KEY environment variable padhta hai
        # Ya hum directly api_key de sakte hain
        self.client = Groq(api_key=self.api_key)
        print(f"  ✅ Groq client ready (key: ...{self.api_key[-6:]})")
        
        # ------------------------------------------------------------------
        # STEP 3: Working Model Dhundho (Auto-Discovery)
        # ------------------------------------------------------------------
        # IMPORTANT FIX: Only TRUE vision models are listed here.
        # llama-4-scout / llama-4-maverick are TEXT-ONLY — they reject image
        # inputs with a 400 error. Sending them a text-only probe and then
        # an image causes silent 0-symbol failures.
        #
        # PRIORITY ORDER (vision accuracy: high → low):
        #   1. llama-3.2-90b-vision-preview  (best for engineering, 90B params)
        #   2. llama-3.2-11b-vision-preview  (smaller but still true vision)
        VISION_MODELS_PRIORITY = [
            "llama-3.2-90b-vision-preview",
            "llama-3.2-11b-vision-preview",
        ]
        
        # Config se jo model set hai woh pehle try karo (only if it's a vision model)
        preferred = CONFIG["GROQ_MODEL"]
        if preferred in VISION_MODELS_PRIORITY:
            VISION_MODELS_PRIORITY.remove(preferred)
        VISION_MODELS_PRIORITY.insert(0, preferred)
        
        self.model_name = self._find_working_model(VISION_MODELS_PRIORITY)
        # FIX: Fallback must ALSO be a vision model — not llama-4-scout (text-only!)
        self.fallback_model = "llama-3.2-11b-vision-preview"
        print(f"  ✅ Active model   : {self.model_name}")
        print(f"  ✅ Fallback model : {self.fallback_model}")
        
        # ------------------------------------------------------------------
        # STEP 4: System Prompt Load
        # ------------------------------------------------------------------
        self.system_prompt = self._load_system_prompt()
        print(f"  ✅ System prompt loaded ({len(self.system_prompt)} chars)")
        
        # ------------------------------------------------------------------
        # STEP 5: Legend Map Load
        # ------------------------------------------------------------------
        self.legend_map = self._load_legend_map()
        print(f"  ✅ Legend map loaded ({len(self.legend_map)} symbols)")
        
        # ------------------------------------------------------------------
        # Retry Settings
        # ------------------------------------------------------------------
        self.max_retries      = CONFIG["MAX_RETRIES"]         # 3
        self.retry_base_delay = CONFIG["RETRY_BASE_DELAY"]    # 2 seconds
        
        # ------------------------------------------------------------------
        # Stats
        # ------------------------------------------------------------------
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens": 0,
            "total_time_seconds": 0,
        }
        
        logging.info(f"HVACClient initialized: model={self.model_name} (Groq)")
        print("  🤖 Groq HVAC Client ready!\n")
    
    # ======================================================================
    # PUBLIC METHODS
    # ======================================================================
    
    def analyze_tile(self, tile_path, legend_path):
        """
        EK tile analyze karo — Groq ko legend + tile images bhejo.
        
        GROQ VISION INPUT FORMAT:
            Groq ka vision model ek special format maangta hai:
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text",      "text": "apna sawaal..."},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,ABC..."}},
                    ]
                }
            ]
            
            "data:image/png;base64,ABC..." ka matlab:
            - "data:"          → yeh data URI hai
            - "image/png"      → PNG format image
            - ";base64,"       → base64 encoding use hui hai
            - "ABC..."         → actual image data (numbers/letters mein)
        
        Parameters:
            tile_path  : Floor plan tile ka path
            legend_path: Legend reference image ka path
        
        Returns:
            dict: Parsed JSON response
            None: Agar fail ho jaye
        """
        
        tile_filename = os.path.basename(tile_path)
        print(f"  🔍 Analyzing: {tile_filename}")
        logging.info(f"Starting analysis: {tile_filename}")
        
        # ------------------------------------------------------------------
        # STEP 1: Images ko Base64 mein convert karo (resize ke saath)
        # ------------------------------------------------------------------
        # Images resize karna kyun zaroori hai?
        #   Badi images = zyada tokens = slow + expensive
        #   1000px se zyada badi images mein quality gain minimal hota hai
        #   Resize karne se tokens ~40% kam ho jaate hain
        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=1000)
            tile_b64   = self._image_to_base64(tile_path,   max_size=1000)
        except FileNotFoundError as e:
            print(f"  ❌ Image not found: {e}")
            return None
        
        # ------------------------------------------------------------------
        # STEP 2: Prompt Build
        # ------------------------------------------------------------------
        prompt_text = self._build_prompt(tile_filename)
        
        # ------------------------------------------------------------------
        # STEP 3: API Call (with retry)
        # ------------------------------------------------------------------
        # Groq ka format OpenAI jaisa hai:
        # client.chat.completions.create(model=..., messages=[...])
        #
        # Message format mein dono images aur text ek saath bhejte hain:
        # [system_role_text, legend_image, instruction_text, tile_image]
        
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                
                # ----- GROQ API CALL -----
                # response_format={"type": "json_object"} = BAHUT IMPORTANT!
                # Yeh Groq ko FORCE karta hai ke response HAMESHA valid JSON ho
                # Bina iske AI kabhi kabhi "Here is the analysis: {...}" likhta hai
                # Isse JSON parse errors practically ZERO ho jaate hain
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},  # ← JSON LOCK (KEY FEATURE)
                    
                    messages=[
                        # ---- System Message ----
                        # AI ko role batao: "tum senior HVAC engineer ho"
                        {
                            "role": "system",
                            "content": prompt_text
                        },
                        
                        # ---- User Message (multimodal) ----
                        # Text + 2 Images ek saath bhejna
                        {
                            "role": "user",
                            "content": [
                                # Part 1: Legend image
                                # "data:image/png;base64,......" format
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{legend_b64}"
                                    }
                                },
                                # Part 2: Legend ko identify karane wala text
                                {
                                    "type": "text",
                                    "text": "This is the REFERENCE LEGEND showing HVAC symbols."
                                },
                                # Part 3: Floor plan tile image
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{tile_b64}"
                                    }
                                },
                                # Part 4: Final instruction
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
                    
                    # AI behavior settings
                    temperature=0.1,      # Low = High accuracy (0.1 not 0, avoids edge cases)
                    max_tokens=4096,    # Maximum response length
                )
                
                elapsed = time.time() - start_time
                
                # ----- Stats Update -----
                self.stats["total_calls"] += 1
                self.stats["total_time_seconds"] += elapsed
                
                # ----- Response Parse -----
                # response.choices[0].message.content = AI ka text response
                raw_text = response.choices[0].message.content
                parsed   = self._parse_json_response(raw_text)
                
                if parsed is not None:
                    self.stats["successful_calls"] += 1
                    
                    # Token usage
                    try:
                        tokens = response.usage.total_tokens
                        self.stats["total_tokens"] += tokens
                        print(f"     ⏱️  {elapsed:.1f}s | Tokens: {tokens}")
                    except Exception:
                        print(f"     ⏱️  {elapsed:.1f}s")
                    
                    logging.info(f"✅ Success: {tile_filename} | {elapsed:.1f}s")
                    return parsed
                else:
                    print(f"     ⚠️  Invalid JSON on attempt {attempt}")
                    logging.warning(f"Invalid JSON: {tile_filename}, attempt {attempt}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"     ❌ Attempt {attempt}/{self.max_retries}: {error_msg[:80]}")
                logging.error(f"API error: {tile_filename}: {error_msg}")
                
                # Rate limit pe automatically fallback model try karo
                if "429" in error_msg or "rate" in error_msg.lower():
                    if self.model_name != self.fallback_model:
                        print(f"     🔄 Rate limited! Switching to fallback: {self.fallback_model}")
                        self.model_name = self.fallback_model
                    wait_time = self.retry_base_delay * (2 ** attempt)
                    print(f"     ⏳ Waiting {wait_time}s...")
                else:
                    wait_time = self.retry_base_delay * (2 ** attempt)
                    if attempt < self.max_retries:
                        print(f"     ⏳ Retrying in {wait_time}s...")
                
                if attempt < self.max_retries:
                    time.sleep(wait_time)
        
        # Saari attempts fail
        self.stats["failed_calls"] += 1
        print(f"  ❌ FAILED after {self.max_retries} attempts: {tile_filename}")
        return None
    
    def analyze_tile_spatial(self, tile_path, legend_path, spatial_prompt=None):
        """
        SPATIAL MODE: Tile analyze karo aur bounding boxes mangno.
        
        Yeh method counting ki jagah LOCATION detect karta hai.
        AI se [ymin, xmin, ymax, xmax] coordinates maangta hai.
        
        Parameters:
            tile_path: Floor plan tile ka path
            legend_path: Legend reference image ka path
            spatial_prompt: Custom spatial prompt (optional)
        
        Returns:
            dict: {"detections": [{"label": "SCD", "box_2d": [y,x,y,x]}, ...]}
        """
        tile_filename = os.path.basename(tile_path)
        print(f"  🔍 [SPATIAL] Analyzing: {tile_filename}")
        
        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=800)
            tile_b64 = self._image_to_base64(tile_path, max_size=1024)
        except FileNotFoundError as e:
            print(f"  ❌ Image not found: {e}")
            return {"detections": []}
        
        # Load spatial prompt
        if spatial_prompt is None:
            prompt_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "prompts", "spatial_prompt.txt"
            )
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    spatial_prompt = f.read()
            else:
                spatial_prompt = (
                    "Detect HVAC symbols. Return JSON with 'detections' array "
                    "containing 'label' and 'box_2d' [ymin,xmin,ymax,xmax] 0-1000."
                )
        
        prompt_text = spatial_prompt.replace("{{TILE_FILENAME}}", tile_filename)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{legend_b64}"
                            }},
                            {"type": "text", "text": "REFERENCE LEGEND (HVAC symbols)."},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{tile_b64}"
                            }},
                            {"type": "text", "text": (
                                "FLOOR PLAN TILE. Detect symbols, return bounding boxes "
                                "[ymin,xmin,ymax,xmax] in 0-1000 range. Pure JSON only."
                            )},
                        ]}
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                
                elapsed = time.time() - start_time
                self.stats["total_calls"] += 1
                self.stats["total_time_seconds"] += elapsed
                
                raw_text = response.choices[0].message.content
                parsed = self._parse_json_response(raw_text)
                
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
                if "429" in error_msg and self.model_name != self.fallback_model:
                    self.model_name = self.fallback_model
                if attempt < self.max_retries:
                    time.sleep(self.retry_base_delay * (2 ** attempt))
        
        self.stats["failed_calls"] += 1
        return {"detections": []}
    
    def extract_and_update_legend(self, legend_path=None):
        """
        Naya legend image scan karke naye acronyms legend_map.json mein add karta hai.
        Yeh method naye drawing projects ke liye zaroori hai.
        """
        if legend_path is None:
            legend_path = CONFIG["LEGEND_IMAGE_PATH"]
            
        print(f"\n  🕵️ AI Legend Extraction: Scanning new symbols from {os.path.basename(legend_path)}")
        logging.info("Starting AI Legend Extraction")
        
        try:
            legend_b64 = self._image_to_base64(legend_path, max_size=1200)
        except FileNotFoundError:
            print(f"  ❌ Legend image not found at {legend_path}")
            return False
            
        prompt_instruction = (
            "You are an expert HVAC engineer. Read this drawing's Legend / Title Block. "
            "Extract all symbols, acronyms, and their FULL NAMES. "
            "Return ONLY a flat JSON dictionary where keys are the Acronym/Symbol "
            "(e.g., 'SCD', 'VAV', 'VD') and values are the Full Description "
            "(e.g., 'SUPPLY CEILING DIFFUSER'). No explanations, no markdown loops, ONLY JSON."
        )
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"     ⏳ Asking Groq AI to extract text (Attempt {attempt})...")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},
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
                                {
                                    "type": "text",
                                    "text": prompt_instruction
                                },
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                
                raw_text = response.choices[0].message.content
                extracted_data = self._parse_json_response(raw_text)
                
                if extracted_data is not None and isinstance(extracted_data, dict):
                    # Current load karo
                    current_map = self._load_legend_map()
                    added_count = 0
                    
                    # Naye keys check karo
                    for key, value in extracted_data.items():
                        # Key ko uppercase aur clean karo
                        k = str(key).strip().upper()
                        v = str(value).strip().upper()
                        
                        if k not in current_map and len(k) < 20:  # Valid acronym format check
                            current_map[k] = v
                            added_count += 1
                            print(f"     ✨ New Symbol Found: {k} -> {v}")
                            
                    if added_count > 0:
                        # Save it back
                        path = CONFIG["LEGEND_MAP_PATH"]
                        with open(path, 'w', encoding='utf-8') as f:
                            json.dump(current_map, f, indent=2, ensure_ascii=False)
                        print(f"  ✅ Updated legend_map.json with {added_count} new entries!")
                        self.legend_map = current_map  # memory mein bhi update karo
                    else:
                        print(f"  ✅ No new symbols found. All matched existing legend_map.json!")
                    
                    return True
                else:
                    print(f"     ⚠️  Invalid JSON received. Retrying...")
                    
            except Exception as e:
                print(f"     ❌ Attempt {attempt} failed: {str(e)[:80]}")
                time.sleep(2)
                
        print("  ❌ Failed to extract legend after all attempts.")
        return False
        
    def get_stats(self):
        """API stats return karo."""
        return self.stats.copy()
    
    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================
    
    def _find_working_model(self, models_list):
        """
        *** CRITICAL FIX ***
        Groq pe kaunsa VISION model available hai woh dhundho.
        
        PURANA BUG:
            Pehle sirf TEXT message bheja jaata tha. Iska matlab:
            - Text-only model (llama-4-scout) bhi PASS kar jaata tha
            - Baad mein jab image bhejte the → 400 error → 0 symbols detected
            - Yeh silent failure tha (koi crash nahi, sirf galat result)
        
        NAYA FIX:
            Ab ek REAL IMAGE (1x1 dummy PNG) bhejte hain test mein.
            Agar model image accept karta hai → vision model confirm!
            Agar reject karta hai → skip (text-only hai yeh model)
        
        Parameters:
            models_list: Priority order mein VISION models ki list
        
        Returns:
            str: Working vision model ka naam
        
        Raises:
            RuntimeError: Agar koi bhi vision model available nahi
        """
        print(f"  🔍 Testing vision capability of models...")
        
        # 1x1 transparent PNG — ultra-small, just to test image acceptance
        # Yeh real HVAC tile nahi hai — sirf probe karne ke liye
        dummy_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQ"
            "DwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        
        # Vision test message — IMAGE + TEXT dono hain
        # Agar model image ko reject kare → exception → next model try karo
        test_messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{dummy_b64}"}
                    },
                    {"type": "text", "text": 'Reply only with: {"vision_ok": true}'}
                ]
            }
        ]
        
        for model in models_list:
            try:
                r = self.client.chat.completions.create(
                    model=model,
                    messages=test_messages,
                    max_tokens=20,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                # Model ne image accept ki aur respond kiya — yeh sahi vision model hai!
                print(f"  ✅ Vision model confirmed: {model}")
                return model
            except Exception as e:
                err = str(e)[:80]
                print(f"     ↳ {model}: FAILED vision test ({err})")
                continue
        
        # Koi bhi vision model nahi mila — clear error do
        raise RuntimeError(
            "\n❌ NO VISION MODEL AVAILABLE ON GROQ!\n"
            "   All models failed the image-acceptance test.\n\n"
            "   Sambhavit wajahaat (Possible reasons):\n"
            "     1. API key ka free tier vision models support nahi karta\n"
            "     2. llama-3.2-90b / 11b vision preview region mein unavailable hai\n"
            "     3. API key expire ya invalid ho gayi\n\n"
            "   Solutions:\n"
            "     → https://console.groq.com pe new API key banao\n"
            "     → Ya OpenAI GPT-4o use karo (supports vision, paid)\n"
            "     → Ya Google Gemini 1.5 Pro use karo (has free tier)\n"
        )
    
    def _image_to_base64(self, image_path, max_size=1000):
        """
        Image file ko base64 string mein convert karo.
        BONUS: Image ko resize bhi karta hai tokens bachane ke liye.
        
        MAX_SIZE KYU?
            Badi images = zyada tokens = slow aur costly
            1000px ke baad extra quality gain minimal hota hai
            Resize se tokens ~40% kam ho jaate hain (faster + cheaper)
        
        Parameters:
            image_path: Image file ka path
            max_size  : Maximum width/height in pixels (default 1000)
        
        Returns:
            str: Base64 encoded string
        """

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # PIL se image load karo
        from PIL import Image as PILImage
        import io
        
        img = PILImage.open(image_path)
        
        # Resize karo agar zaroorat ho
        # thumbnail() = aspect ratio maintain karta hai (distort nahi hoti)
        if img.width > max_size or img.height > max_size:
            original_size = f"{img.width}x{img.height}"
            img.thumbnail((max_size, max_size), PILImage.LANCZOS)
            # LANCZOS = best quality resize algorithm
        
        # PIL image → PNG bytes → base64 string
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def _load_system_prompt(self):
        """System prompt file load karo."""
        path = CONFIG["SYSTEM_PROMPT_PATH"]
        if not os.path.exists(path):
            raise FileNotFoundError(f"System prompt not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_legend_map(self):
        """Legend map JSON load karo."""
        path = CONFIG["LEGEND_MAP_PATH"]
        if not os.path.exists(path):
            raise FileNotFoundError(f"Legend map not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _build_prompt(self, tile_filename):
        """System prompt mein tile filename inject karo."""
        return self.system_prompt.replace("{{TILE_FILENAME}}", tile_filename)
    
    def _parse_json_response(self, raw_text):
        """
        AI response text → JSON dictionary.
        
        3-LAYER PARSING:
            Layer 1: Direct json.loads() --- agar response pure JSON hai
            Layer 2: Markdown fences hatao --- ```json...``` se JSON nikalo
            Layer 3: Brace matching --- { se leke } tak extract karo
        """
        if not raw_text or not raw_text.strip():
            return None
        
        cleaned = raw_text.strip()
        
        # Layer 1: Direct
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Layer 2: Markdown fences
        no_fences = re.sub(r'```(?:json)?\s*', '', cleaned).strip()
        try:
            return json.loads(no_fences)
        except json.JSONDecodeError:
            pass
        
        # Layer 3: { ... } extract
        first = cleaned.find('{')
        last  = cleaned.rfind('}')
        if first != -1 and last > first:
            try:
                return json.loads(cleaned[first:last + 1])
            except json.JSONDecodeError:
                pass
        
        logging.error(f"JSON parse failed. Sample: {cleaned[:200]}")
        return None
    
    def save_response(self, response_data, tile_filename, output_dir=None):
        """
        AI response ko JSON file mein save karo.
        tile_y2700_x3600.png → tile_y2700_x3600_result.json
        """
        if output_dir is None:
            output_dir = CONFIG["TEST_RESPONSES_DIR"]
        
        os.makedirs(output_dir, exist_ok=True)
        result_filename = tile_filename.replace(".png", "_result.json")
        result_path = os.path.join(output_dir, result_filename)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        
        print(f"     💾 Saved: {result_filename}")
        logging.info(f"Response saved: {result_path}")
        return result_path


# ============================================================================
# SINGLE TILE TEST — Day 9
# ============================================================================

if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 9: GROQ VISION CLIENT — SINGLE TILE TEST")
    print("=" * 60)
    
    # Client initialize
    try:
        client = GeminiHVACClient()
    except ValueError as e:
        print(f"\n  ❌ {e}")
        sys.exit(1)
    
    # Densest tile (845KB = most HVAC content)
    test_tile   = os.path.join(CONFIG["TILE_OUTPUT"], "tile_y2700_x3600.png")
    legend_path = CONFIG["LEGEND_IMAGE_PATH"]
    
    if not os.path.exists(test_tile):
        print(f"  ❌ Tile not found: {test_tile}")
        print(f"  👉 Run day7_full_pipeline.py first")
        sys.exit(1)
    
    if not os.path.exists(legend_path):
        print(f"  ❌ Legend not found: {legend_path}")
        sys.exit(1)
    
    print(f"\n  📷 Test tile : {os.path.basename(test_tile)}")
    print(f"  📋 Legend    : {os.path.basename(legend_path)}")
    print(f"  🤖 Model     : {client.model_name}")
    print(f"  {'─' * 50}")
    print(f"\n  ⏳ Sending to Groq (usually 5-15 seconds)...")
    
    result = client.analyze_tile(test_tile, legend_path)
    
    if result:
        print(f"\n  ✅ SUCCESS! AI Response Received:")
        print(f"  {'─' * 50}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        symbols   = result.get("symbols", [])
        total_qty = sum(s.get("quantity", 0) for s in symbols)
        ducts     = len(result.get("duct_runs_detected", []))
        
        print(f"\n  {'─' * 50}")
        print(f"  📊 Quick Summary:")
        print(f"     Unique symbol types : {len(symbols)}")
        print(f"     Total symbol count  : {total_qty}")
        print(f"     Duct runs detected  : {ducts}")
        print(f"     Human review needed : {result.get('requires_human_review', False)}")
        
        client.save_response(result, "tile_y2700_x3600.png")
    else:
        print(f"\n  ❌ FAILED — No valid response")
        print(f"  👉 Check logs/system.log for details")
    
    stats = client.get_stats()
    print(f"\n  📈 API Stats:")
    print(f"     Model        : {client.model_name}")
    print(f"     Total calls  : {stats['total_calls']}")
    print(f"     Successful   : {stats['successful_calls']}")
    print(f"     Total time   : {stats['total_time_seconds']:.1f}s")
    print(f"     Total tokens : {stats['total_tokens']}")
    
    print(f"\n  🎉 DAY 9 COMPLETE!")
    print("=" * 60)
