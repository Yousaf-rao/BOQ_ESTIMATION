# ============================================================================
# phase2_brain_engine.py — Day 13: Full Phase 2 Pipeline Integration
# ============================================================================
#
# 🎯 OBJECTIVE: Phase 2 ka MASTER ENGINE — sab kuch EK command mein!
#   Jaise Day 7 mein Phase 1 ka master engine tha (PDF → tiles),
#   yeh Phase 2 ka master engine hai (tiles → BOQ).
#
# REAL-WORLD ANALOGY:
#   Phase 1 = Factory mein raw material tayyar karna (PDF → images)
#   Phase 2 = Factory mein product banana (images → BOQ)
#   
#   Day  9 = Machine ka trial run (single tile test)
#   Day 10 = Machine full production pe (batch processing)
#   Day 11 = Quality check department (validation & parsing)
#   Day 12 = Final packaging (aggregation & summary)
#   Day 13 = FACTORY MANAGER — sab ko coordinate karta hai (THIS FILE!)
#
# PIPELINE FLOW:
#   ┌────────────────────────────────────────────────┐
#   │  PHASE 2 — AI BRAIN PIPELINE                   │
#   ├────────────────────────────────────────────────┤
#   │                                                 │
#   │  Step 1: Load Phase 1 Outputs                  │
#   │     ↓  (tiles, legend, legend_map)             │
#   │                                                 │
#   │  Step 2: Initialize Gemini Client              │
#   │     ↓  (API key, model, system prompt)         │
#   │                                                 │
#   │  Step 3: Process All 20 Tiles                  │
#   │     ↓  (batch processing with rate limiting)   │
#   │                                                 │
#   │  Step 4: Validate & Parse Responses            │
#   │     ↓  (normalize names, check confidence)     │
#   │                                                 │
#   │  Step 5: Aggregate Results                     │
#   │     ↓  (merge counts, deduplication)           │
#   │                                                 │
#   │  Step 6: Generate Final Report                 │
#   │     ↓  (_merged_counts.json + console report)  │
#   │                                                 │
#   │  ✅ OUTPUT: Building-Level HVAC BOQ             │
#   └────────────────────────────────────────────────┘
#
# 📝 HOW TO RUN:  python phase2_brain_engine.py
#
# ZARURI:
#   - Phase 1 complete honi chahiye (Day 7 run ho chuka ho)
#   - .env mein GEMINI_API_KEY hona chahiye
# ============================================================================

import os
import sys
import json
import time
import logging
from datetime import datetime

# --------------------------------------------------------------------------
# Project modules import karo — sab days ka kaam yahan use hoga!
# --------------------------------------------------------------------------
from config import CONFIG, validate_config

# Day 9:  Gemini se baat karne wala client
from gemini_client import GeminiHVACClient

# Day 10: Saari tiles batch mein process karne wala
from tile_processor import TileProcessor

# Day 11: AI responses ko validate aur clean karne wala
from response_parser import ResponseParser

# Day 12: Saari tiles ke results ko merge karne wala
from results_aggregator import ResultsAggregator

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class HVACBrainEngine:
    """
    Phase 2 ka MASTER ENGINE — sab steps coordinate karta hai.
    
    ARCHITECTURE:
        Day 9  (GeminiHVACClient)   → AI se baat karo
        Day 10 (TileProcessor)      → Saari tiles process karo
        Day 11 (ResponseParser)     → Responses validate + clean karo
        Day 12 (ResultsAggregator)  → Results merge karo → BOQ
        
        Yeh engine (Day 13) in sab ko SAHI ORDER mein call karta hai
        aur errors gracefully handle karta hai.
    
    DESIGN PRINCIPLE — "Orchestrator Pattern":
        Yeh class khud koi heavy kaam nahi karti.
        Sirf doosri classes ko coordinate karti hai.
        Jaise orchestra ka conductor — khud instrument nahi bajata,
        but sabko sahi waqt pe sahi notes bajwata hai!
    """
    
    def __init__(self):
        """
        Engine initialize karo.
        
        NOTE: Yahan sirf basic setup hai.
        Heavy initialization (Gemini client, etc.) run_full_phase2()
        mein hogi — taake agar Phase 1 check fail ho toh 
        bekaar mein Gemini initialize na ho.
        """
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = {}  # Har step ka result yahan store hoga
        
        logging.info("=" * 50)
        logging.info("HVACBrainEngine initialized")
    
    def run_full_phase2(self):
        """
        Complete Phase 2 pipeline run karo — tiles se BOQ tak!
        
        STEPS:
            0. Config validate karo
            1. Phase 1 outputs verify karo (tiles, legend exist karti hain?)
            2. Gemini client initialize karo
            3. Saari tiles process karo (batch + rate limiting)
            4. AI responses validate + normalize karo
            5. Results aggregate karo (merge + deduplication)
            6. Final report generate karo
        
        Returns:
            bool: True agar pipeline successfully complete hui, False otherwise
        """
        
        pipeline_start = time.time()
        
        print("\n" + "🔷" * 30)
        print("  🧠 HVAC BRAIN ENGINE — PHASE 2 PIPELINE")
        print("🔷" * 30)
        print(f"  Model: {CONFIG.get('GROQ_MODEL', 'llama-4-scout-17b')} (Groq)")
        print(f"  Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ================================================================
        # STEP 0: Config Validate
        # ================================================================
        print(f"\n{'─' * 50}")
        print(f"  📋 STEP 0: Validating Configuration")
        print(f"{'─' * 50}")
        
        try:
            validate_config()
        except ValueError as e:
            print(f"  ❌ {e}")
            return False
        
        # API key check (Groq)
        if not CONFIG.get("GROQ_API_KEY"):
            print(f"  ❌ GROQ_API_KEY not found in .env!")
            print(f"  👉 Get free key from: https://console.groq.com")
            print(f"  👉 Add to .env: GROQ_API_KEY=gsk_your_key_here")
            return False
        
        print(f"  ✅ Groq API key found")
        
        # ================================================================
        # STEP 1: Phase 1 Outputs Verify
        # ================================================================
        print(f"\n{'─' * 50}")
        print(f"  📋 STEP 1: Verifying Phase 1 Outputs")
        print(f"{'─' * 50}")
        
        phase1_check = self._verify_phase1_outputs()
        
        if not phase1_check["ok"]:
            print(f"\n  ❌ Phase 1 outputs missing!")
            print(f"  👉 Run: python day7_full_pipeline.py")
            self.results["step1"] = {"status": "❌ FAILED — Phase 1 incomplete"}
            return False
        
        self.results["step1"] = {
            "status": "✅ SUCCESS",
            "tiles_found": phase1_check["tiles_count"],
            "legend_found": True,
        }
        
        # ================================================================
        # STEP 2: Batch Tile Processing (Day 9 + Day 10)
        # ================================================================
        print(f"\n{'─' * 50}")
        print(f"  📋 STEP 2: Processing All Tiles with Gemini AI")
        print(f"{'─' * 50}")
        
        try:
            processor = TileProcessor()
            processing_stats = processor.process_all_tiles()
            
            self.results["step2"] = {
                "status": "✅ SUCCESS",
                "tiles_total": processing_stats["total_tiles"],
                "processed": processing_stats["processed"],
                "skipped": processing_stats["skipped"],
                "successful": processing_stats["successful"],
                "failed": processing_stats["failed"],
                "time_seconds": round(processing_stats["total_time_seconds"], 1),
            }
            
            # Agar saari tiles fail ho gayin toh ruko
            if processing_stats["successful"] == 0 and processing_stats["skipped"] == 0:
                print(f"\n  ❌ No tiles were successfully processed!")
                return False
            
        except Exception as e:
            print(f"  ❌ Batch processing failed: {e}")
            logging.error(f"Step 2 failed: {e}")
            self.results["step2"] = {"status": f"❌ FAILED — {e}"}
            return False
        
        # ================================================================
        # STEP 3: Validate & Normalize Responses (Day 11)
        # ================================================================
        print(f"\n{'─' * 50}")
        print(f"  📋 STEP 3: Validating & Normalizing AI Responses")
        print(f"{'─' * 50}")
        
        try:
            parser = ResponseParser()
            
            # Saari result files load karo aur validate karo
            results_dir = CONFIG["AI_RESULTS_DIR"]
            result_files = sorted([
                f for f in os.listdir(results_dir)
                if f.endswith("_result.json") and not f.startswith("_")
            ])
            
            validated_count = 0
            
            for rf in result_files:
                filepath = os.path.join(results_dir, rf)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Validate + Normalize + Confidence Filter
                    processed, is_valid, errors, warnings = parser.process_response(data)
                    
                    if is_valid:
                        validated_count += 1
                        
                        # Processed version overwrite karo
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(processed, f, indent=2, ensure_ascii=False)
                        
                        symbols_count = len(processed.get("symbols", []))
                        print(f"     ✅ {rf}: {symbols_count} symbols (validated)")
                    else:
                        print(f"     ⚠️  {rf}: Validation issues — {errors[:2]}")
                        
                except Exception as e:
                    print(f"     ❌ {rf}: {e}")
            
            # Validation report generate karo
            validation_report = parser.generate_validation_report()
            
            self.results["step3"] = {
                "status": "✅ SUCCESS",
                "files_validated": len(result_files),
                "valid": validated_count,
                "symbols_normalized": parser.validation_stats["symbols_normalized"],
                "low_confidence_flagged": parser.validation_stats["low_confidence_flagged"],
            }
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            logging.error(f"Step 3 failed: {e}")
            self.results["step3"] = {"status": f"⚠️ PARTIAL — {e}"}
            # Validation fail hone pe bhi aage chalo — results toh hain
        
        # ================================================================
        # STEP 4: Aggregate Results (Day 12)
        # ================================================================
        print(f"\n{'─' * 50}")
        print(f"  📋 STEP 4: Aggregating Results → Building-Level BOQ")
        print(f"{'─' * 50}")
        
        try:
            aggregator = ResultsAggregator()
            
            # Merge all tiles
            counts = aggregator.merge_tile_results()
            
            if counts:
                # Generate summary (saves _merged_counts.json + prints report)
                summary = aggregator.generate_summary()
                
                self.results["step4"] = {
                    "status": "✅ SUCCESS",
                    "unique_symbol_types": len(counts),
                    "grand_total_items": summary.get("grand_total_items", 0),
                    "categories": len(summary.get("category_totals", {})),
                }
            else:
                self.results["step4"] = {"status": "⚠️ — No counts to aggregate"}
                
        except Exception as e:
            print(f"  ❌ Aggregation failed: {e}")
            logging.error(f"Step 4 failed: {e}")
            self.results["step4"] = {"status": f"❌ FAILED — {e}"}
        
        # ================================================================
        # FINAL REPORT
        # ================================================================
        pipeline_elapsed = time.time() - pipeline_start
        
        self._print_final_report(pipeline_elapsed)
        self._save_phase2_report(pipeline_elapsed)
        
        return True
    
    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================
    
    def _verify_phase1_outputs(self):
        """
        Phase 1 ke outputs verify karo — tiles, legend, legend_map.
        
        Returns:
            dict: {"ok": True/False, "tiles_count": int, "missing": []}
        """
        
        result = {"ok": True, "tiles_count": 0, "missing": []}
        
        # Check 1: Tile map
        tile_map_path = CONFIG["TILE_MAP_PATH"]
        if os.path.exists(tile_map_path):
            with open(tile_map_path, 'r') as f:
                tile_map = json.load(f)
            result["tiles_count"] = tile_map.get("total_tiles", 0)
            print(f"  ✅ Tile map: {result['tiles_count']} tiles")
        else:
            result["ok"] = False
            result["missing"].append("tile_map.json")
            print(f"  ❌ Tile map: MISSING")
        
        # Check 2: Legend image
        legend_path = CONFIG["LEGEND_IMAGE_PATH"]
        if os.path.exists(legend_path):
            size_kb = os.path.getsize(legend_path) / 1024
            print(f"  ✅ Legend image: {size_kb:.0f} KB")
        else:
            result["ok"] = False
            result["missing"].append("legend_reference.png")
            print(f"  ❌ Legend image: MISSING")
        
        # Check 3: Legend map JSON
        map_path = CONFIG["LEGEND_MAP_PATH"]
        if os.path.exists(map_path):
            with open(map_path, 'r') as f:
                legend_map = json.load(f)
            print(f"  ✅ Legend map: {len(legend_map)} symbols")
        else:
            result["ok"] = False
            result["missing"].append("legend_map.json")
            print(f"  ❌ Legend map: MISSING")
        
        # Check 4: System prompt
        prompt_path = CONFIG["SYSTEM_PROMPT_PATH"]
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                chars = len(f.read())
            print(f"  ✅ System prompt: {chars} chars")
        else:
            result["ok"] = False
            result["missing"].append("system_prompt.txt")
            print(f"  ❌ System prompt: MISSING")
        
        # Check 5: At least some tiles exist
        tiles_dir = CONFIG["TILE_OUTPUT"]
        if os.path.exists(tiles_dir):
            tile_files = [f for f in os.listdir(tiles_dir) if f.endswith('.png')]
            if len(tile_files) == 0:
                result["ok"] = False
                result["missing"].append("tile images")
                print(f"  ❌ Tile images: NONE found")
            else:
                print(f"  ✅ Tile images: {len(tile_files)} files")
        else:
            result["ok"] = False
            result["missing"].append("output_tiles directory")
            print(f"  ❌ Tiles directory: MISSING")
        
        return result
    
    def _print_final_report(self, elapsed):
        """Phase 2 ka final summary report console pe print karo."""
        
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        print(f"\n{'🟢' * 30}")
        print(f"  📋 PHASE 2 — FINAL REPORT")
        print(f"{'🟢' * 30}")
        
        step_labels = {
            "step1": "Phase 1 Verification",
            "step2": "Tile Processing (Gemini AI)",
            "step3": "Response Validation",
            "step4": "Results Aggregation",
        }
        
        for step_name, step_data in self.results.items():
            label = step_labels.get(step_name, step_name)
            print(f"\n  {label}:")
            
            for key, val in step_data.items():
                print(f"    {key:25s}: {val}")
        
        print(f"\n  ⏱️  Total Pipeline Time: {minutes}m {seconds}s")
        print(f"\n  📁 OUTPUT FILES:")
        print(f"     Per-tile results  → {CONFIG['AI_RESULTS_DIR']}/")
        print(f"     Merged BOQ        → {CONFIG['AI_RESULTS_DIR']}/_merged_counts.json")
        print(f"     Validation report → {CONFIG['AI_RESULTS_DIR']}/_validation_report.json")
        print(f"     Processing log    → {CONFIG['AI_RESULTS_DIR']}/_processing_log.json")
        print(f"     System log        → {CONFIG['LOG_FILE']}")
        
        print(f"\n  🎉 PHASE 2 COMPLETE!")
        print(f"  👉 NEXT: Phase 3 — Export to Excel BOQ with market rates")
        print(f"{'🟢' * 30}")
    
    def _save_phase2_report(self, elapsed):
        """Phase 2 ka full report JSON mein save karo."""
        
        report = {
            "pipeline": "Phase 2 — HVAC AI Brain Engine",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_time_seconds": round(elapsed, 2),
            "model_used": CONFIG.get("GROQ_MODEL", "llama-vision"),
            "config_used": {
                "tile_size": CONFIG["TILE_SIZE"],
                "overlap": CONFIG["OVERLAP"],
                "api_delay": CONFIG["API_DELAY_SECONDS"],
                "max_retries": CONFIG["MAX_RETRIES"],
            },
            "step_results": self.results,
        }
        
        report_path = os.path.join(self.base_dir, "logs", "phase2_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Phase 2 report saved: {report_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 PHASE 2: HVAC AI BRAIN ENGINE")
    print("  📅 Day 13 — Full Pipeline Integration")
    print("=" * 60)
    
    engine = HVACBrainEngine()
    
    try:
        success = engine.run_full_phase2()
    except KeyboardInterrupt:
        print(f"\n\n  ⏹️  Pipeline stopped by user (Ctrl+C)")
        print(f"  👉 Re-run to continue (resume mode will skip done tiles)")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {e}")
        logging.error(f"Pipeline crash: {e}", exc_info=True)
        sys.exit(1)
    
    if not success:
        print(f"\n  ⚠️  Pipeline did not complete successfully.")
        print(f"  👉 Check logs/system.log for details.")
        sys.exit(1)
    
    print(f"\n  🎉 DAY 13 COMPLETE — PHASE 2 DONE!")
    print("=" * 60)
