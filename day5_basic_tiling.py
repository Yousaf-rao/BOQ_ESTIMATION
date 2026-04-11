# ============================================================================
# day5_basic_tiling.py — Day 5: Intelligent Tiling Logic (Part A)
# ============================================================================
#
# 🎯 OBJECTIVE: Badi image ko chhote equal-sized tiles mein kaatna
#   AI models ~4096px limit rakhte hain, hamari image ~10000px hai
#   Solution: 1200x1200 tiles bana do
#
# 📝 HOW TO RUN:  python day5_basic_tiling.py
# 🔗 DEPENDS ON: config.py, Day 2 output
# ============================================================================

import cv2
import numpy as np
import os
import logging
import time
import shutil

from config import CONFIG

os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class BasicTiler:
    """
    Image ko equal-sized grid tiles mein divide karta hai (bina overlap).
    
    VISUAL:
        ┌────────┬────────┬────────┬────────┐
        │ (0,0)  │ (0,1)  │ (0,2)  │ (0,3)  │  ← Row 0
        ├────────┼────────┼────────┼────────┤
        │ (1,0)  │ (1,1)  │ (1,2)  │ (1,3)  │  ← Row 1
        ├────────┼────────┼────────┼────────┤
        │ (2,0)  │ (2,1)  │ (2,2)  │ (2,3)  │  ← Row 2
        └────────┴────────┴────────┴────────┘
    """
    
    def __init__(self):
        self.tile_size = CONFIG["TILE_SIZE"]
        self.min_tile_size = CONFIG.get("MIN_TILE_SIZE", 200)
        self.output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "tiles_basic"
        )
        logging.info(f"BasicTiler initialized: tile_size={self.tile_size}")
    
    def prepare_output_folder(self):
        """Output folder clean karke fresh start deta hai."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
            print(f"  🗑️  Cleaned old tiles")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_tiles(self, img):
        """
        Image ko grid tiles mein divide karta hai.
        
        LOOP LOGIC:
            for y in range(0, h, tile_size):   ← Har 1200px neeche jump
                for x in range(0, w, tile_size): ← Har 1200px right jump
                    tile = img[y:y+1200, x:x+1200]  ← Crop square
        
        Returns: int — Total tiles generated
        """
        print(f"\n  🔲 Generating tiles ({self.tile_size}x{self.tile_size})...")
        start_time = time.time()
        
        h, w = img.shape[:2]
        print(f"     Source: {w} x {h} pixels")
        
        cols = -(-w // self.tile_size)  # Ceiling division
        rows = -(-h // self.tile_size)
        print(f"     Grid: {cols} cols × {rows} rows = ~{rows*cols} tiles")
        
        self.prepare_output_folder()
        
        tile_count = 0
        skipped = 0
        
        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                # Edge safety: don't go past image boundary
                y_end = min(y + self.tile_size, h)
                x_end = min(x + self.tile_size, w)
                
                # Skip tiny edge tiles
                if (y_end - y) < self.min_tile_size or (x_end - x) < self.min_tile_size:
                    skipped += 1
                    continue
                
                tile = img[y:y_end, x:x_end]
                
                row_idx = y // self.tile_size
                col_idx = x // self.tile_size
                filename = f"tile_r{row_idx}_c{col_idx}.png"
                cv2.imwrite(os.path.join(self.output_dir, filename), tile)
                tile_count += 1
        
        elapsed = time.time() - start_time
        print(f"     ✅ {tile_count} tiles generated, {skipped} skipped ({elapsed:.2f}s)")
        logging.info(f"Basic tiling: {tile_count} tiles in {elapsed:.2f}s")
        return tile_count
    
    def list_tiles(self):
        """Generated tiles ki list dikhata hai."""
        if not os.path.exists(self.output_dir):
            return []
        tiles = sorted(f for f in os.listdir(self.output_dir) if f.endswith('.png'))
        print(f"\n  📋 {len(tiles)} tiles in output:")
        for t in tiles[:8]:
            fp = os.path.join(self.output_dir, t)
            img = cv2.imread(fp)
            if img is not None:
                print(f"     {t:25s} — {img.shape[1]}x{img.shape[0]} px")
        if len(tiles) > 8:
            print(f"     ... +{len(tiles)-8} more")
        return tiles


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  🚀 DAY 5: BASIC TILING (NO OVERLAP)")
    print("=" * 60)
    
    tiler = BasicTiler()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img = None
    
    for path in [
        os.path.join(base_dir, "data", "floor_plan_only.png"),
        os.path.join(base_dir, "data", "drawing_high_res.png"),
    ]:
        if os.path.exists(path):
            print(f"\n  📷 Using: {os.path.basename(path)}")
            img = cv2.imread(path)
            break
    
    if img is None and os.path.exists(CONFIG["INPUT_PATH"]):
        from day2_pdf_to_image import PDFConverter
        img = PDFConverter().convert(CONFIG["INPUT_PATH"])
    
    if img is None:
        print("  ⚠️  No source found — using demo image")
        img = np.ones((3600, 4800, 3), dtype=np.uint8) * 240
    
    total = tiler.generate_tiles(img)
    tiler.list_tiles()
    
    print(f"\n  ⚠️  PROBLEM: Symbols at tile edges get CUT!")
    print(f"     → Day 6 solves this with OVERLAP tiling")
    print(f"\n  🎉 DAY 5 COMPLETE!")
