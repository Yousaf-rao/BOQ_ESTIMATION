# ============================================================================
# day6_overlap_tiling.py — Day 6: The "Overlap Hack" (Advanced Tiling)
# ============================================================================
#
# 🎯 OBJECTIVE: Day 5 ki PROBLEM solve karna!
#   Day 5 mein tiles ke EDGES pe symbols kat jaate the.
#   Overlap tiling mein har tile apne neighbour ke saath 300px share karti hai.
#   Isse EVERY symbol at least ek tile mein POORA dikhta hai.
#
# VISUAL: (Overlap vs No Overlap)
#
#   NO OVERLAP (Day 5):          WITH OVERLAP (Day 6):
#   ┌──────┬──────┐              ┌──────────┐
#   │ Tile │ Tile │              │  Tile A   │
#   │  A   │  B   │              │     ┌─────┼────┐
#   │      │      │              │     │OVRP │    │
#   └──────┴──────┘              └─────┼─────┘    │
#   ↑ Symbol cut!                      │  Tile B  │
#                                      └──────────┘
#                                ↑ Symbol appears in BOTH tiles!
#
# 📝 HOW TO RUN:  python day6_overlap_tiling.py
# ============================================================================

import cv2
import numpy as np
import os
import logging
import time
import shutil
import json

from config import CONFIG

os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class OverlapTiler:
    """
    Overlapping tiles generate karta hai — symbols kabhi nahi katenge!
    
    KEY CONCEPT — STEP SIZE:
        tile_size = 1200px
        overlap   = 300px
        step      = tile_size - overlap = 1200 - 300 = 900px
        
        Window 900px jump karti hai, but 1200px ka area capture karti hai.
        Matlab har do adjacent tiles 300px share karte hain.
    
    MATH EXAMPLE:
        Image width = 4800px, tile_size=1200, step=900
        
        Tile 1: x=0    to x=1200   (covers 0-1200)
        Tile 2: x=900  to x=2100   (covers 900-2100)  ← 300px overlap!
        Tile 3: x=1800 to x=3000   (covers 1800-3000) ← 300px overlap!
        Tile 4: x=2700 to x=3900
        Tile 5: x=3600 to x=4800
        
        Total = 5 tiles (vs 4 without overlap)
        Extra tiles = zyada coverage = ZERO missed symbols!
    """
    
    def __init__(self):
        self.tile_size = CONFIG["TILE_SIZE"]        # 1200px
        self.overlap = CONFIG["OVERLAP"]            # 300px
        self.step = self.tile_size - self.overlap    # 900px
        self.min_tile = CONFIG.get("MIN_TILE_SIZE", 200)
        self.output_dir = CONFIG["TILE_OUTPUT"]     # Final output folder
        self.grayscale = CONFIG.get("GRAYSCALE_MODE", False)
        
        logging.info(
            f"OverlapTiler: tile={self.tile_size}, "
            f"overlap={self.overlap}, step={self.step}"
        )
    
    def prepare_output_folder(self):
        """Clean output folder for fresh tiles."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_tiles(self, img):
        """
        Overlapping tiles generate karta hai.
        
        ALGORITHM:
            step = tile_size - overlap  (e.g., 1200 - 300 = 900)
            
            for y in range(0, height, step):    ← 900px vertical jump
                for x in range(0, width, step): ← 900px horizontal jump
                    crop 1200×1200 area at (x, y)
                    save tile with coordinates in filename
        
        Returns: int — Total tiles, also saves tile map JSON
        """
        print(f"\n  🔲 Generating OVERLAP tiles...")
        print(f"     Tile size : {self.tile_size}px")
        print(f"     Overlap   : {self.overlap}px")
        print(f"     Step size : {self.step}px")
        start_time = time.time()
        
        h, w = img.shape[:2]
        print(f"     Source    : {w} x {h} pixels")
        
        self.prepare_output_folder()
        
        tile_count = 0
        tile_map = []  # Metadata for each tile (Phase 2 mein AI ko denge)
        
        # --- MAIN TILING LOOP ---
        # range(0, h, step) → y = 0, 900, 1800, 2700, ...
        for y in range(0, h, self.step):
            for x in range(0, w, self.step):
                
                # --- Boundaries with safety ---
                y_end = min(y + self.tile_size, h)
                x_end = min(x + self.tile_size, w)
                
                tile_h = y_end - y
                tile_w = x_end - x
                
                # Skip tiny tiles
                if tile_h < self.min_tile or tile_w < self.min_tile:
                    continue
                
                # --- CROP ---
                tile = img[y:y_end, x:x_end]
                
                # --- Optional: Grayscale ---
                if self.grayscale and len(tile.shape) == 3:
                    tile = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
                
                # --- Skip blank tiles ---
                # Agar tile almost fully white hai toh skip (empty area)
                if self._is_blank_tile(tile):
                    continue
                
                # --- Save ---
                # Filename mein y aur x coordinates hain
                # Isse Phase 2 mein pata chalega tile kahan se aayi
                filename = f"tile_y{y}_x{x}.png"
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, tile)
                
                # --- Tile metadata ---
                tile_map.append({
                    "filename": filename,
                    "y_start": y,
                    "x_start": x,
                    "y_end": y_end,
                    "x_end": x_end,
                    "width": tile_w,
                    "height": tile_h,
                })
                
                tile_count += 1
        
        elapsed = time.time() - start_time
        
        # --- Save tile map (JSON) ---
        # Yeh file Phase 2 mein AI results ko original coordinates mein
        # map karne ke liye use hogi
        map_path = os.path.join(self.output_dir, "_tile_map.json")
        with open(map_path, 'w') as f:
            json.dump({
                "source_width": w,
                "source_height": h,
                "tile_size": self.tile_size,
                "overlap": self.overlap,
                "step": self.step,
                "total_tiles": tile_count,
                "tiles": tile_map
            }, f, indent=2)
        
        print(f"\n  📊 Results:")
        print(f"     Total tiles  : {tile_count}")
        print(f"     Tile map     : _tile_map.json")
        print(f"     Time         : {elapsed:.2f}s")
        
        logging.info(f"Overlap tiling complete: {tile_count} tiles in {elapsed:.2f}s")
        return tile_count
    
    def _is_blank_tile(self, tile, threshold=250, blank_pct=0.98):
        """
        Check: kya tile almost empty (white) hai?
        Blank tiles AI ko bhejne ka koi faida nahi.
        
        Logic: Agar 98% pixels ka brightness > 250 hai toh blank hai.
        """
        if len(tile.shape) == 3:
            gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
        else:
            gray = tile
        
        white_pixels = np.sum(gray > threshold)
        total_pixels = gray.shape[0] * gray.shape[1]
        
        return (white_pixels / total_pixels) > blank_pct
    
    def get_tile_stats(self):
        """Output folder ki stats dikhata hai."""
        if not os.path.exists(self.output_dir):
            return {}
        
        tiles = [f for f in os.listdir(self.output_dir) 
                 if f.endswith('.png')]
        
        total_size = sum(
            os.path.getsize(os.path.join(self.output_dir, f))
            for f in tiles
        )
        
        stats = {
            "total_tiles": len(tiles),
            "total_size_mb": round(total_size / (1024*1024), 2),
            "avg_size_kb": round(total_size / max(len(tiles), 1) / 1024, 1),
        }
        
        print(f"\n  📊 Tile Statistics:")
        print(f"     Count     : {stats['total_tiles']}")
        print(f"     Total Size: {stats['total_size_mb']} MB")
        print(f"     Avg Size  : {stats['avg_size_kb']} KB per tile")
        
        return stats


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  🚀 DAY 6: OVERLAP TILING (THE FIX)")
    print("=" * 60)
    
    tiler = OverlapTiler()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img = None
    
    # Find source image
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
        print("  ⚠️  No source — using demo image")
        img = np.ones((3600, 4800, 3), dtype=np.uint8) * 240
        for i in range(0, 4800, 400):
            cv2.circle(img, (i, 1800), 30, (0, 0, 200), -1)
    
    total = tiler.generate_tiles(img)
    tiler.get_tile_stats()
    
    print(f"\n  ✅ Overlap ensures ZERO cut symbols!")
    print(f"  📁 Tiles saved in: {CONFIG['TILE_OUTPUT']}")
    print(f"\n  🎉 DAY 6 COMPLETE! Ready for Day 7 (Integration).")
