# ============================================================================
# day7_full_pipeline.py — Day 7: Full Integration Pipeline
# ============================================================================
#
# 🎯 OBJECTIVE: Day 1-6 ka saara kaam EK command mein!
#   Input:  drawing.pdf (RAPCO/EPC shop drawing)
#   Output: legend_reference.png + overlapping tiles folder + tile map JSON
#
# 📝 HOW TO RUN:  python day7_full_pipeline.py
#
# PIPELINE FLOW:
#   PDF → [Day2: High-Res Image] → [Day4: Legend + Floor Plan]
#       → [Day6: Overlap Tiles] → ✅ DONE (Ready for Phase 2 AI)
# ============================================================================

import os
import sys
import time
import logging
import json

from config import CONFIG, validate_config

os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class HVACVisionEngine:
    """
    Master Engine — Phase 1 ka complete pipeline ek class mein.
    
    ARCHITECTURE:
        Day 2 (PDFConverter) → Day 4 (LegendExtractor) → Day 6 (OverlapTiler)
        
        Har day ka code apni file mein hai, yeh engine unko
        sahi order mein call karta hai aur errors handle karta hai.
    """
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = {}  # Pipeline results store karo
        logging.info("=" * 50)
        logging.info("HVACVisionEngine initialized")
    
    def run_full_phase1(self, pdf_path=None):
        """
        Complete Phase 1 pipeline run karta hai.
        
        Steps:
            1. Config validate karo
            2. PDF → High-res image (Day 2)
            3. Legend extract karo (Day 4)
            4. Overlap tiles banao (Day 6)
            5. Summary report generate karo
        
        Parameters:
            pdf_path: PDF file path. None = config se lega.
        """
        
        pipeline_start = time.time()
        
        print("\n" + "🔷" * 30)
        print("  🚀 HVAC VISION ENGINE — PHASE 1 PIPELINE")
        print("🔷" * 30)
        
        if pdf_path is None:
            pdf_path = CONFIG["INPUT_PATH"]
        
        # ============================
        # STEP 0: Validate Config
        # ============================
        print("\n📋 STEP 0: Validating Configuration...")
        print("-" * 50)
        try:
            validate_config()
        except ValueError as e:
            print(f"  ❌ {e}")
            return False
        
        # ============================
        # STEP 1: PDF → Image (Day 2)
        # ============================
        print(f"\n📋 STEP 1: PDF → High-Resolution Image [Day 2]")
        print("-" * 50)
        
        try:
            from day2_pdf_to_image import PDFConverter
            
            converter = PDFConverter()
            image = converter.convert(pdf_path)
            
            # Save full high-res image
            high_res_path = os.path.join(self.base_dir, "data", "drawing_high_res.png")
            converter.save_image(image, high_res_path)
            
            info = converter.get_image_info(image)
            self.results["step1"] = {
                "status": "✅ SUCCESS",
                "image_size": f"{info['width_px']}x{info['height_px']}",
                "memory_mb": info['memory_mb'],
                "dpi": 72 * CONFIG['ZOOM'],
            }
            print(f"  ✅ Image: {info['width_px']}x{info['height_px']} @ {72*CONFIG['ZOOM']:.0f} DPI")
            
        except FileNotFoundError:
            print(f"  ❌ PDF not found: {pdf_path}")
            print(f"  👉 Place your PDF at: {pdf_path}")
            self.results["step1"] = {"status": "❌ FAILED — PDF not found"}
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            logging.error(f"Step 1 failed: {e}")
            self.results["step1"] = {"status": f"❌ FAILED — {e}"}
            return False
        
        # ============================
        # STEP 2: Legend Extract (Day 4)
        # ============================
        print(f"\n📋 STEP 2: Legend / Title Block Extraction [Day 4]")
        print("-" * 50)
        
        try:
            from day4_legend_extractor import LegendExtractor
            
            extractor = LegendExtractor()
            legend_img, floor_plan_img = extractor.extract_from_image(image)
            
            legend_path = extractor.save_legend(legend_img)
            floor_path = extractor.save_floor_plan(floor_plan_img)
            
            analysis = extractor.analyze_legend(legend_img)
            
            self.results["step2"] = {
                "status": "✅ SUCCESS",
                "legend_size": f"{legend_img.shape[1]}x{legend_img.shape[0]}",
                "floor_plan_size": f"{floor_plan_img.shape[1]}x{floor_plan_img.shape[0]}",
                "legend_path": legend_path,
            }
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            logging.error(f"Step 2 failed: {e}")
            floor_plan_img = image  # Fallback: use full image
            self.results["step2"] = {"status": f"⚠️ PARTIAL — using full image"}
        
        # ============================
        # STEP 2.5: AI Legend Auto-Discovery
        # ============================
        print(f"\n📋 STEP 2.5: AI Legend Auto-Discovery [Groq Vision]")
        print("-" * 50)
        
        try:
            from gemini_client import GeminiHVACClient
            
            client = GeminiHVACClient()
            if 'legend_path' in locals() and legend_path:
                client.extract_and_update_legend(legend_path)
            self.results["step2_5"] = {"status": "✅ SUCCESS"}
            
        except Exception as e:
            print(f"  ⚠️  AI Legend extraction skipped or failed: {e}")
            logging.warning(f"Step 2.5 failed (AI Legend): {e}")
            self.results["step2_5"] = {"status": f"⚠️ SKIPPED - {e}"}

        # ============================
        # STEP 3: Overlap Tiles (Day 6)
        # ============================
        print(f"\n📋 STEP 3: Overlapping Tile Generation [Day 6]")
        print("-" * 50)
        
        try:
            from day6_overlap_tiling import OverlapTiler
            
            tiler = OverlapTiler()
            total_tiles = tiler.generate_tiles(floor_plan_img)
            stats = tiler.get_tile_stats()
            
            self.results["step3"] = {
                "status": "✅ SUCCESS",
                "total_tiles": total_tiles,
                "total_size_mb": stats.get('total_size_mb', 0),
            }
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            logging.error(f"Step 3 failed: {e}")
            self.results["step3"] = {"status": f"❌ FAILED — {e}"}
            return False
        
        # ============================
        # FINAL REPORT
        # ============================
        pipeline_elapsed = time.time() - pipeline_start
        
        self._print_final_report(pipeline_elapsed)
        self._save_report(pipeline_elapsed)
        
        return True
    
    def _print_final_report(self, elapsed):
        """Console pe final summary print karta hai."""
        
        print("\n" + "🟢" * 30)
        print("  📋 PHASE 1 — FINAL REPORT")
        print("🟢" * 30)
        
        for step_name, step_data in self.results.items():
            step_label = {
                "step1": "PDF → Image",
                "step2": "Legend Extract",
                "step3": "Tile Generation"
            }.get(step_name, step_name)
            
            print(f"\n  {step_label}:")
            for key, val in step_data.items():
                print(f"    {key:20s}: {val}")
        
        print(f"\n  ⏱️  Total Pipeline Time: {elapsed:.2f} seconds")
        print(f"\n  📁 OUTPUT LOCATIONS:")
        print(f"     Legend    → {CONFIG['LEGEND_OUTPUT']}/")
        print(f"     Tiles     → {CONFIG['TILE_OUTPUT']}/")
        print(f"     Logs      → {CONFIG['LOG_FILE']}")
        print(f"\n  🎉 PHASE 1 COMPLETE!")
        print(f"  👉 NEXT: Phase 2 — Connect tiles to Gemini/GPT-4 Vision AI")
        print("🟢" * 30)
    
    def _save_report(self, elapsed):
        """Report ko JSON file mein save karta hai."""
        report = {
            "pipeline": "Phase 1 — HVAC Vision Preprocessing",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time_seconds": round(elapsed, 2),
            "config_used": {
                "zoom": CONFIG["ZOOM"],
                "tile_size": CONFIG["TILE_SIZE"],
                "overlap": CONFIG["OVERLAP"],
                "legend_pct": CONFIG["LEGEND_WIDTH_PCT"],
            },
            "results": self.results,
        }
        
        report_path = os.path.join(self.base_dir, "logs", "phase1_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"Phase 1 report saved: {report_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    
    engine = HVACVisionEngine()
    
    # Check for command-line PDF path argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"  📄 Using CLI argument: {pdf_path}")
        success = engine.run_full_phase1(pdf_path)
    else:
        success = engine.run_full_phase1()
    
    if not success:
        print("\n  ⚠️  Pipeline did not complete successfully.")
        print("  👉 Check logs/system.log for details.")
        sys.exit(1)
