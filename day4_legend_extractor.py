# ============================================================================
# day4_legend_extractor.py — Day 4: The "Legend" / Title Block Extractor
# ============================================================================
#
# 🎯 OBJECTIVE: (Kya karenge?)
#   Engineering drawings mein RIGHT side pe ek "Legend" ya "Title Block" hota hai.
#   Yeh block drawing ka "cheat sheet" hai — ismein symbols ke naam hote hain.
#   
#   Example (RAPCO drawing):
#   ┌────────────────────────────────────┬──────────┐
#   │                                    │ LEGEND   │
#   │    MAIN FLOOR PLAN                 │ -------- │
#   │    (ducts, diffusers, etc.)        │ ○ Supply │
#   │                                    │ □ Return │
#   │                                    │ △ Exhaust│
#   │                                    │          │
#   │                                    │ TITLE:   │
#   │                                    │ RAPCO    │
#   └────────────────────────────────────┴──────────┘
#          ← ~78% Floor Plan →            ← ~22% →
#
#   Is script ka kaam hai:
#   1. Yeh Legend area automatically detect aur crop karna
#   2. Isko alag se save karna (legend_reference.png)
#   3. Floor plan area bhi alag save karna
#
# 📝 HOW TO RUN:
#       python day4_legend_extractor.py
#
# 🔗 DEPENDS ON:
#   - config.py (LEGEND_WIDTH_PCT setting)
#   - Day 2 ka output (drawing_high_res.png) ya actual PDF
#
# ============================================================================

import cv2
import numpy as np
import os
import logging
import time

from config import CONFIG

# Logging setup
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class LegendExtractor:
    """
    Engineering drawing se Legend/Title Block extract karta hai.
    
    ENGINEERING CONTEXT:
        EPC (Engineering, Procurement, Construction) drawings mein
        title block ALWAYS right side pe hota hai. Yeh standard hai:
        - ANSI/ISO standards follow karte hain
        - Title block mein hota hai:
            * Project name
            * Drawing number
            * Revision history
            * Symbol legend (MOST IMPORTANT for us!)
            * Scale information
            * Engineer signatures
    
    USAGE:
        extractor = LegendExtractor()
        legend, floor_plan = extractor.extract_from_image(image)
        # ya
        legend, floor_plan = extractor.extract_from_pdf("drawing.pdf")
    """
    
    def __init__(self):
        """Constructor — Settings load karo"""
        self.legend_width_pct = CONFIG["LEGEND_WIDTH_PCT"]   # 0.22 = 22%
        self.legend_output = CONFIG["LEGEND_OUTPUT"]          # Save folder
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Output folder banao
        os.makedirs(self.legend_output, exist_ok=True)
        
        logging.info(f"LegendExtractor initialized: legend_width={self.legend_width_pct*100:.0f}%")
    
    
    def extract_from_image(self, img):
        """
        Image se Legend area aur Floor Plan area alag karta hai.
        
        ALGORITHM:
            1. Image ki total width nikalo
            2. Legend width calculate karo: total_width × LEGEND_WIDTH_PCT
            3. RIGHT side se utna hissa crop karo = LEGEND
            4. LEFT side ka bacha hua hissa = FLOOR PLAN
        
        VISUAL:
            Image Width = 5000 pixels
            Legend PCT   = 0.22 (22%)
            Legend Width = 5000 × 0.22 = 1100 pixels
            
            ┌──── Floor Plan (3900px) ────┬── Legend (1100px) ──┐
            │  img[0:h, 0:3900]           │ img[0:h, 3900:5000]│
            └─────────────────────────────┴─────────────────────┘
            x=0                     x=3900                x=5000
        
        Parameters:
            img : Full drawing image (NumPy array, BGR)
        
        Returns:
            tuple: (legend_image, floor_plan_image)
        """
        
        print(f"\n  🔍 Extracting Legend from image...")
        start_time = time.time()
        
        # --- Image dimensions ---
        h, w = img.shape[:2]
        print(f"     Full image size: {w} x {h} pixels")
        
        # --- Legend width calculate karo ---
        # int() se round off hota hai (pixels mein fraction nahi hota)
        legend_w = int(w * self.legend_width_pct)
        
        # Split point = jahan se legend shuru hota hai
        split_x = w - legend_w
        
        print(f"     Legend width: {self.legend_width_pct*100:.0f}% = {legend_w} pixels")
        print(f"     Split point: x = {split_x}")
        
        # --- CROP: Legend Area (Right Side) ---
        # img[y_start:y_end, x_start:x_end]
        # y_start=0, y_end=h    → poori height lo
        # x_start=split_x, x_end=w → right side ka portion
        
        legend_img = img[0:h, split_x:w].copy()
        
        # --- CROP: Floor Plan Area (Left Side) ---
        # x_start=0, x_end=split_x → left side ka portion
        
        floor_plan_img = img[0:h, 0:split_x].copy()
        
        elapsed = time.time() - start_time
        
        print(f"     Legend size    : {legend_img.shape[1]} x {legend_img.shape[0]} pixels")
        print(f"     Floor Plan size: {floor_plan_img.shape[1]} x {floor_plan_img.shape[0]} pixels")
        print(f"     Time taken    : {elapsed:.3f}s")
        
        logging.info(
            f"Legend extracted: {legend_img.shape[1]}x{legend_img.shape[0]} | "
            f"Floor Plan: {floor_plan_img.shape[1]}x{floor_plan_img.shape[0]}"
        )
        
        return legend_img, floor_plan_img
    
    
    def extract_from_pdf(self, pdf_path=None):
        """
        PDF se directly Legend extract karta hai (Day 2 ka code use karke).
        
        Parameters:
            pdf_path : PDF file ka path. None = config se lega.
        
        Returns:
            tuple: (legend_image, floor_plan_image)
        """
        
        if pdf_path is None:
            pdf_path = CONFIG["INPUT_PATH"]
        
        print(f"\n  📄 Extracting Legend from PDF: {os.path.basename(pdf_path)}")
        
        # Day 2 ka PDFConverter use karo
        from day2_pdf_to_image import PDFConverter
        
        converter = PDFConverter()
        full_image = converter.convert(pdf_path)
        
        return self.extract_from_image(full_image)
    
    
    def save_legend(self, legend_img, filename="legend_reference.png"):
        """
        Legend image ko file mein save karta hai.
        
        Parameters:
            legend_img : Legend ka cropped image (NumPy array)
            filename   : File ka naam
        
        Returns:
            str — Saved file ka full path
        """
        
        save_path = os.path.join(self.legend_output, filename)
        
        success = cv2.imwrite(save_path, legend_img)
        
        if success:
            file_size_kb = os.path.getsize(save_path) / 1024
            print(f"  💾 Legend saved: {save_path} ({file_size_kb:.1f} KB)")
            logging.info(f"Legend saved to: {save_path}")
            return save_path
        else:
            print(f"  ❌ Failed to save legend!")
            logging.error(f"Failed to save legend to: {save_path}")
            return None
    
    
    def save_floor_plan(self, floor_plan_img, filename="floor_plan_only.png"):
        """
        Floor plan (bina legend ke) save karta hai.
        
        Parameters:
            floor_plan_img : Floor plan ka cropped image (NumPy array)
            filename       : File ka naam
        
        Returns:
            str — Saved file ka full path
        """
        
        save_path = os.path.join(self.base_dir, "data", filename)
        
        success = cv2.imwrite(save_path, floor_plan_img)
        
        if success:
            file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
            print(f"  💾 Floor Plan saved: {save_path} ({file_size_mb:.2f} MB)")
            logging.info(f"Floor plan saved to: {save_path}")
            return save_path
        else:
            print(f"  ❌ Failed to save floor plan!")
            return None
    
    
    def analyze_legend(self, legend_img):
        """
        Legend image ki basic analysis karta hai.
        Phase 2 mein AI isko detail se read karega,
        abhi sirf basic statistics check karte hain.
        
        Parameters:
            legend_img : Legend ka cropped image (NumPy array)
        
        Returns:
            dict — Analysis results
        """
        
        print(f"\n  🔬 Analyzing Legend Image...")
        
        h, w = legend_img.shape[:2]
        
        # Grayscale convert karo analysis ke liye
        if len(legend_img.shape) == 3:
            gray = cv2.cvtColor(legend_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = legend_img
        
        # --- Average brightness ---
        # Dark areas = text/symbols, Light areas = background
        avg_brightness = np.mean(gray)
        
        # --- Text density estimate ---
        # Threshold: 128 se kam = dark (text/lines), 128 se zyada = light (background)
        # cv2.threshold() = har pixel ko black ya white banata hai
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        
        # Dark pixels ka percentage = content density
        dark_pixels = np.sum(binary > 0)
        total_pixels = h * w
        content_density = (dark_pixels / total_pixels) * 100
        
        # --- Edge detection (content complexity) ---
        # Canny edge detection lines aur shapes dhundta hai
        edges = cv2.Canny(gray, 50, 150)
        edge_density = (np.sum(edges > 0) / total_pixels) * 100
        
        analysis = {
            "width": w,
            "height": h,
            "avg_brightness": round(avg_brightness, 1),
            "content_density_pct": round(content_density, 1),
            "edge_density_pct": round(edge_density, 1),
        }
        
        print(f"     Legend Size      : {w} x {h} pixels")
        print(f"     Avg Brightness   : {avg_brightness:.1f} / 255 "
              f"({'Light bg' if avg_brightness > 200 else 'Has content'})")
        print(f"     Content Density  : {content_density:.1f}%")
        print(f"     Edge Complexity  : {edge_density:.1f}%")
        
        # Quality check
        if content_density < 1:
            print(f"     ⚠️  WARNING: Legend seems too empty — check LEGEND_WIDTH_PCT in config.py")
        elif content_density > 40:
            print(f"     ⚠️  WARNING: Legend is too dense — might be cutting into floor plan")
        else:
            print(f"     ✅ Legend content looks reasonable!")
        
        return analysis


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 4: LEGEND / TITLE BLOCK EXTRACTOR")
    print("=" * 60)
    
    extractor = LegendExtractor()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # --- Source image dhundho ---
    # Pehle Day 2 ka output try karo
    high_res_path = os.path.join(base_dir, "data", "drawing_high_res.png")
    
    legend_img = None
    floor_plan_img = None
    
    if os.path.exists(high_res_path):
        # Day 2 ka output hai — usse use karo
        print(f"\n  📷 Using Day 2 output: drawing_high_res.png")
        img = cv2.imread(high_res_path)
        
        if img is not None:
            legend_img, floor_plan_img = extractor.extract_from_image(img)
    
    elif os.path.exists(CONFIG["INPUT_PATH"]):
        # Direct PDF se extract karo
        print(f"\n  📄 No pre-rendered image found. Converting from PDF...")
        legend_img, floor_plan_img = extractor.extract_from_pdf()
    
    else:
        # Demo image banao
        print(f"\n  ⚠️  No PDF or image found. Creating demo for practice...")
        from day3_opencv_basics import OpenCVBasics
        basics = OpenCVBasics()
        demo_img, _ = basics.create_demo_image()
        legend_img, floor_plan_img = extractor.extract_from_image(demo_img)
    
    # --- Save outputs ---
    if legend_img is not None:
        print("\n" + "-" * 60)
        extractor.save_legend(legend_img)
        extractor.save_floor_plan(floor_plan_img)
        
        # --- Analyze legend ---
        print("\n" + "-" * 60)
        analysis = extractor.analyze_legend(legend_img)
    
    # --- SUMMARY ---
    print("\n" + "=" * 60)
    print("  📋 DAY 4 SUMMARY")
    print("=" * 60)
    print(f"  Legend Width Setting : {CONFIG['LEGEND_WIDTH_PCT']*100:.0f}% of total width")
    if legend_img is not None:
        print(f"  Legend Image         : ✅ Saved to data/legends/")
        print(f"  Floor Plan Image     : ✅ Saved to data/")
        print(f"  Legend Analysis      : ✅ Done")
    else:
        print(f"  ❌ No image could be processed")
    print(f"\n  💡 TIP: Agar legend cut sahi nahi lagi, toh config.py mein")
    print(f"         LEGEND_WIDTH_PCT change karo (e.g., 0.15 to 0.30)")
    print(f"\n  🎉 DAY 4 COMPLETE! Ready for Day 5.")
    print("=" * 60)
