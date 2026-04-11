# ============================================================================
# tile_processor.py — Day 10: Tile Batch Processor (All 20 Tiles)
# ============================================================================
#
# 🎯 OBJECTIVE: SAARI 20 tiles ko Gemini se analyze karo — ek ek karke!
#   Day 9 mein humne EK tile test ki thi.
#   Aaj hum SAARI tiles ek loop mein process karenge.
#
# REAL-WORLD ANALOGY:
#   Sochiye aap ek factory mein QC inspector hain.
#   Day 9 = Ek product check kiya (pilot test)
#   Day 10 = Ab SAARE products check karo (batch processing)
#   Par dhyaan raho — machine ko rest bhi chahiye (rate limiting)!
#
# FEATURES:
#   ✅ Loop through all 20 tiles from _tile_map.json
#   ✅ Rate limiting (2 second delay between calls)
#   ✅ Progress tracking: "Processing tile 7/20: tile_y1800_x3600.png..."
#   ✅ Resume capability: Skip already-processed tiles on re-run
#   ✅ Cost tracking: Log token usage per call
#   ✅ Per-tile result storage in data/ai_results/
#
# 📝 HOW TO RUN:  python tile_processor.py
#
# ZARURI:
#   - .env mein GEMINI_API_KEY hona chahiye
#   - Phase 1 complete honi chahiye (tiles + legend exist karna chahiye)
# ============================================================================

import os
import sys
import json
import time
import logging

# --------------------------------------------------------------------------
# Apni project files import karo
# --------------------------------------------------------------------------
from config import CONFIG                      # Central settings
from gemini_client import GeminiHVACClient     # Day 9 ka Gemini client

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TileProcessor:
    """
    Saari tiles ko batch mein process karta hai — ek ek karke Gemini ko bhejta hai.
    
    YEH CLASS KYA KARTI HAI:
        1. _tile_map.json load karta hai (Phase 1 se 20 tiles ki info)
        2. GeminiHVACClient initialize karta hai
        3. Har tile ko legend + tile image ke saath Gemini ko bhejta hai
        4. Response ko data/ai_results/ mein save karta hai
        5. Already processed tiles ko SKIP karta hai (resume capability)
        6. Progress aur cost track karta hai
    
    RESUME CAPABILITY:
        Agar processing beech mein ruk jaaye (internet gir jaaye, etc.),
        toh dobara run karne pe ALREADY DONE tiles skip ho jaenge.
        Yeh bahut useful hai — 20 mein se 15 ho chuki hain toh sirf 5 karegi!
    
    RATE LIMITING:
        Google ke servers pe zyada load mat daalo.
        Har API call ke baad 2 second ruko.
        Free tier mein limit hai — 15 RPM (requests per minute).
    """
    
    def __init__(self):
        """
        Processor initialize karo — tile map load karo, client banao.
        
        STEPS:
            1. _tile_map.json load karo (Phase 1 ka output)
            2. GeminiHVACClient initialize karo (Day 9)
            3. Output directory banao (data/ai_results/)
            4. Legend image path set karo
        """
        
        print("\n  🔲 Initializing Tile Processor...")
        
        # ------------------------------------------------------------------
        # STEP 1: Tile Map Load Karo
        # ------------------------------------------------------------------
        # _tile_map.json mein Phase 1 (Day 6) ne saari tiles ki info rakhi hai:
        # - filename, y_start, x_start, y_end, x_end, width, height
        # Yeh humein batata hai ke KAUN SI tiles process karni hain
        self.tile_map = self._load_tile_map()
        self.tiles = self.tile_map.get("tiles", [])
        print(f"  ✅ Tile map loaded: {len(self.tiles)} tiles")
        
        # ------------------------------------------------------------------
        # STEP 2: Gemini Client Initialize Karo
        # ------------------------------------------------------------------
        # Day 9 ka client — yeh actually Gemini se baat karta hai
        self.client = GeminiHVACClient()
        
        # ------------------------------------------------------------------
        # STEP 3: Output Directory Banao
        # ------------------------------------------------------------------
        # Har tile ka result alag JSON file mein save hoga
        # data/ai_results/tile_y2700_x3600_result.json
        self.results_dir = CONFIG["AI_RESULTS_DIR"]
        os.makedirs(self.results_dir, exist_ok=True)
        
        # ------------------------------------------------------------------
        # STEP 4: Paths Set Karo
        # ------------------------------------------------------------------
        self.legend_path = CONFIG["LEGEND_IMAGE_PATH"]
        self.tiles_dir = CONFIG["TILE_OUTPUT"]
        self.api_delay = CONFIG["API_DELAY_SECONDS"]   # 2 seconds between calls
        
        # ------------------------------------------------------------------
        # Processing Stats
        # ------------------------------------------------------------------
        self.processing_stats = {
            "total_tiles": len(self.tiles),
            "processed": 0,
            "skipped": 0,           # Already processed (resume)
            "successful": 0,
            "failed": 0,
            "total_time_seconds": 0,
            "start_time": None,
        }
        
        logging.info(f"TileProcessor initialized: {len(self.tiles)} tiles")
        print("  🔲 Tile Processor ready!\n")
    
    # ======================================================================
    # PUBLIC METHODS
    # ======================================================================
    
    def process_all_tiles(self):
        """
        SAARI tiles process karo — yeh Day 10 ka MAIN function hai!
        
        FLOW:
            1. Har tile ke liye check karo — pehle se done toh nahi?
            2. Agar done hai toh SKIP (resume capability)
            3. Agar nahi toh Gemini ko bhejo
            4. Response save karo
            5. 2 second ruko (rate limiting)
            6. Progress dikhao: "🔄 [7/20] tile_y1800_x3600.png..."
        
        Returns:
            dict: Processing statistics (kitni done, kitni fail, time, etc.)
        """
        
        total = len(self.tiles)
        
        print("🔷" * 30)
        print(f"  🚀 BATCH PROCESSING: {total} TILES")
        print("🔷" * 30)
        print(f"  ⏱️  API delay     : {self.api_delay}s between calls")
        print(f"  📁 Results dir   : {self.results_dir}")
        print(f"  🤖 Model         : {self.client.model_name}")
        
        # Estimate time
        # Har tile ~15-30 seconds + 2s delay = ~20s average
        estimated_minutes = (total * 20) / 60
        print(f"  ⏰ Est. time     : ~{estimated_minutes:.0f} minutes")
        print(f"  {'─' * 50}\n")
        
        self.processing_stats["start_time"] = time.time()
        
        # ------------------------------------------------------------------
        # MAIN LOOP — Har tile ek ek karke
        # ------------------------------------------------------------------
        for index, tile_info in enumerate(self.tiles, 1):
            
            # tile_info = {"filename": "tile_y2700_x3600.png", "y_start": 2700, ...}
            filename = tile_info["filename"]
            
            # ---- PROGRESS DISPLAY ----
            # "[7/20]" format mein dikhao — human ko samajh aaye kitna baaki hai
            progress_pct = (index / total) * 100
            print(f"  🔄 [{index}/{total}] ({progress_pct:.0f}%) {filename}")
            
            # ---- RESUME CHECK ----
            # Kya yeh tile pehle se process ho chuki hai?
            # Agar result file already exist karti hai toh SKIP karo
            result_filename = filename.replace(".png", "_result.json")
            result_path = os.path.join(self.results_dir, result_filename)
            
            if os.path.exists(result_path):
                print(f"     ⏭️  Already processed — SKIPPING")
                self.processing_stats["skipped"] += 1
                continue
            
            # ---- PROCESS THIS TILE ----
            result = self.process_single_tile(tile_info)
            
            if result:
                self.processing_stats["successful"] += 1
            else:
                self.processing_stats["failed"] += 1
            
            self.processing_stats["processed"] += 1
            
            # ---- RATE LIMITING ----
            # Last tile ke baad wait karne ki zaroorat nahi
            if index < total:
                print(f"     ⏳ Waiting {self.api_delay}s (rate limit)...")
                time.sleep(self.api_delay)
        
        # ------------------------------------------------------------------
        # FINAL STATS
        # ------------------------------------------------------------------
        total_elapsed = time.time() - self.processing_stats["start_time"]
        self.processing_stats["total_time_seconds"] = total_elapsed
        
        self._print_batch_report()
        self._save_processing_log()
        
        return self.processing_stats
    
    def process_single_tile(self, tile_info):
        """
        EK tile process karo — Gemini ko bhejo aur result save karo.
        
        Parameters:
            tile_info: dict from _tile_map.json
                       {"filename": "...", "y_start": 0, "x_start": 0, ...}
        
        Returns:
            dict: Parsed result, ya None agar fail
        
        FLOW:
            1. Tile image ka full path banao
            2. GeminiHVACClient.analyze_tile() call karo
            3. Response mein tile coordinates add karo (map se)
            4. data/ai_results/ mein save karo
        """
        
        filename = tile_info["filename"]
        tile_path = os.path.join(self.tiles_dir, filename)
        
        # Check ke tile file exist karti hai
        if not os.path.exists(tile_path):
            print(f"     ❌ Tile file not found: {filename}")
            logging.error(f"Tile not found: {tile_path}")
            return None
        
        # ------------------------------------------------------------------
        # Gemini ko bhejo
        # ------------------------------------------------------------------
        result = self.client.analyze_tile(tile_path, self.legend_path)
        
        if result is None:
            print(f"     ❌ Analysis failed for {filename}")
            return None
        
        # ------------------------------------------------------------------
        # Tile coordinates inject karo (agar AI ne nahi diye)
        # ------------------------------------------------------------------
        # AI ka response mein tile_coordinates honi chahiye,
        # but SAFETY ke liye hum _tile_map.json se bhi add kar dete hain
        # Yeh aggregation mein deduplication ke liye zaroori hai
        if "tile_coordinates" not in result or not result["tile_coordinates"]:
            result["tile_coordinates"] = {
                "y_start": tile_info["y_start"],
                "x_start": tile_info["x_start"],
                "y_end": tile_info["y_end"],
                "x_end": tile_info["x_end"],
            }
        
        # Tile ID bhi set karo agar missing hai
        if "tile_id" not in result or not result["tile_id"]:
            result["tile_id"] = filename
        
        # ------------------------------------------------------------------
        # Save karo
        # ------------------------------------------------------------------
        self.client.save_response(result, filename, output_dir=self.results_dir)
        
        # Quick summary print karo
        symbols = result.get("symbols", [])
        total_count = sum(s.get("quantity", 0) for s in symbols)
        print(f"     ✅ Found: {len(symbols)} types, {total_count} total symbols")
        
        return result
    
    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================
    
    def _load_tile_map(self):
        """
        _tile_map.json load karo — Phase 1 (Day 6) ka output.
        
        Isme har tile ki info hai:
            - filename (e.g., "tile_y2700_x3600.png")
            - y_start, x_start, y_end, x_end (pixel coordinates)
            - width, height
        
        Returns:
            dict: Complete tile map data
        """
        map_path = CONFIG["TILE_MAP_PATH"]
        
        if not os.path.exists(map_path):
            raise FileNotFoundError(
                f"Tile map not found: {map_path}\n"
                f"👉 Run Day 7 pipeline first to generate tiles"
            )
        
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _print_batch_report(self):
        """Processing ka final report console pe print karo."""
        
        stats = self.processing_stats
        elapsed = stats["total_time_seconds"]
        
        # Minutes aur seconds mein convert
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        print(f"\n{'🟢' * 30}")
        print(f"  📋 BATCH PROCESSING — FINAL REPORT")
        print(f"{'🟢' * 30}")
        print(f"")
        print(f"  📊 Results:")
        print(f"     Total tiles    : {stats['total_tiles']}")
        print(f"     Processed      : {stats['processed']}")
        print(f"     Skipped (done) : {stats['skipped']}")
        print(f"     Successful     : {stats['successful']}")
        print(f"     Failed         : {stats['failed']}")
        print(f"     Total time     : {minutes}m {seconds}s")
        
        # Avg time per tile
        active_processed = stats['successful'] + stats['failed']
        if active_processed > 0:
            avg_time = elapsed / active_processed
            print(f"     Avg per tile   : {avg_time:.1f}s")
        
        # Gemini client stats
        client_stats = self.client.get_stats()
        print(f"\n  🤖 API Stats:")
        print(f"     API calls      : {client_stats['total_calls']}")
        print(f"     Total tokens   : {client_stats['total_tokens']}")
        
        # Cost estimate
        # Gemini 1.5 Flash: ~$0.00035 per 1K tokens (input + output)
        # Gemini 1.5 Pro:   ~$0.00175 per 1K tokens (input + output)
        if client_stats['total_tokens'] > 0:
            if "flash" in self.client.model_name:
                cost = (client_stats['total_tokens'] / 1000) * 0.00035
            else:
                cost = (client_stats['total_tokens'] / 1000) * 0.00175
            print(f"     Est. cost      : ${cost:.4f}")
        
        print(f"\n  📁 Output: {self.results_dir}")
        
        if stats['failed'] > 0:
            print(f"\n  ⚠️  {stats['failed']} tiles failed — re-run to retry them!")
        else:
            print(f"\n  🎉 All tiles processed successfully!")
        
        print(f"{'🟢' * 30}")
    
    def _save_processing_log(self):
        """
        Processing stats ko JSON log file mein save karo.
        Yeh debugging aur tracking ke liye useful hai.
        """
        
        log_data = {
            "pipeline": "Phase 2 — Tile Batch Processing (Day 10)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": self.client.model_name,
            "processing_stats": self.processing_stats,
            "api_stats": self.client.get_stats(),
        }
        
        log_path = os.path.join(self.results_dir, "_processing_log.json")
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Processing log saved: {log_path}")
        print(f"\n  📝 Processing log: _processing_log.json")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 10: TILE BATCH PROCESSOR")
    print("=" * 60)
    
    # ------------------------------------------------------------------
    # STEP 1: Check ke Phase 1 outputs exist karti hain
    # ------------------------------------------------------------------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    checks = {
        "Legend image": CONFIG["LEGEND_IMAGE_PATH"],
        "Tile map": CONFIG["TILE_MAP_PATH"],
        "System prompt": CONFIG["SYSTEM_PROMPT_PATH"],
        "Legend map": CONFIG["LEGEND_MAP_PATH"],
    }
    
    all_ok = True
    for name, path in checks.items():
        if os.path.exists(path):
            print(f"  ✅ {name}: Found")
        else:
            print(f"  ❌ {name}: MISSING — {path}")
            all_ok = False
    
    if not all_ok:
        print(f"\n  ❌ Phase 1 outputs missing! Run Day 7 pipeline first.")
        sys.exit(1)
    
    # ------------------------------------------------------------------
    # STEP 2: Batch Processing Start Karo!
    # ------------------------------------------------------------------
    try:
        processor = TileProcessor()
        stats = processor.process_all_tiles()
    except ValueError as e:
        print(f"\n  ❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        # User ne Ctrl+C press kiya — gracefully ruko
        print(f"\n\n  ⏹️  Processing stopped by user (Ctrl+C)")
        print(f"  👉 Re-run to continue from where you left off (resume mode)")
        sys.exit(0)
    
    print(f"\n  🎉 DAY 10 COMPLETE!")
    print("=" * 60)
