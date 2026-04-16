import os
import cv2
import numpy as np
from pathlib import Path

# CONFIG
INPUT_FOLDER = Path("data/high_res_drawings_no_legend")
OUTPUT_FOLDER = Path("data/training_backgrounds_2000")
TILE_SIZE = 2000
TARGET_TILES_PER_IMAGE = 7  # Ek drawing se 7 tiles leingy taake diversity barkarar rahe
TOTAL_IMAGES_NEEDED = 40


# Density parameters for YOLO background
# Hamein itna density chahiye jahan lines hon (cad data) par itna dense na ho ke text ka black blob ban jaye
MIN_DENSITY = 0.015 
MAX_DENSITY = 0.15

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Purane backgrounds hata do agar hain
for f in OUTPUT_FOLDER.glob("*.png"):
    f.unlink()

def get_edge_density(gray_tile):
    """Calculate ratio of edges to total area."""
    blur = cv2.GaussianBlur(gray_tile, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)
    return np.sum(edges > 0) / edges.size

def extract_best_tiles(image_path, num_tiles):
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Skipping {image_path.name} (Irregular format)")
        return []

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    candidates = []
    stride = int(TILE_SIZE * 0.5)  # 50% overlap ke sath search karenge
    
    # Grid search for valid tiles
    for y in range(0, h - TILE_SIZE, stride):
        for x in range(0, w - TILE_SIZE, stride):
            tile_gray = gray[y:y+TILE_SIZE, x:x+TILE_SIZE]
            
            # Simple check for pure white/black before edge density
            # Agar tile 95% se zyada white hai, to ignore karo
            white_pixels = np.sum(tile_gray > 240)
            if white_pixels / tile_gray.size > 0.95:
                continue
                
            d = get_edge_density(tile_gray)
            if MIN_DENSITY < d < MAX_DENSITY:
                candidates.append((d, y, x))

    if not candidates:
        return []

    # Analysis/Selection logic:
    # 1. Hamein "medium" density wale chahiye (around 0.06) jo realistic CAD map dikhayen
    # Sort candidates by how close they are to ideal density (0.06)
    candidates.sort(key=lambda t: abs(t[0] - 0.06))

    # 2. Hamein spatially diverse tiles chahiye taake ek hi jagah ki 5 copy na ban jayein
    selected = []
    min_dist = TILE_SIZE * 0.8  # Kam se kam itna distance ho tiles ke darmiyan
    
    for (d, cy, cx) in candidates:
        too_close = any(np.hypot(cx - sx, cy - sy) < min_dist for (_, sy, sx) in selected)
        if not too_close:
            selected.append((d, cy, cx))
        if len(selected) >= num_tiles:
            break

    # Extract successful crops
    tiles = []
    for (d, y, x) in selected:
        tile = img[y:y+TILE_SIZE, x:x+TILE_SIZE]
        tiles.append(tile)
        
    return tiles

def main():
    images = list(INPUT_FOLDER.glob("*.png"))
    print(f"Found {len(images)} high-res images for analysis.\n")
    
    saved_count = 0
    for img_path in images:
        if saved_count >= TOTAL_IMAGES_NEEDED:
            break
            
        print(f"Analyzing: {img_path.name}")
        tiles = extract_best_tiles(img_path, TARGET_TILES_PER_IMAGE)
        
        for i, tile in enumerate(tiles):
            out_file = OUTPUT_FOLDER / f"bg_tile_{saved_count+1:03d}.png"
            cv2.imwrite(str(out_file), tile)
            saved_count += 1
            if saved_count >= TOTAL_IMAGES_NEEDED:
                break
                
        print(f"   => Extracted {len(tiles)} best optimal tiles.\n")

    print(f"SUCCESS! Created {saved_count} highly optimized {TILE_SIZE}x{TILE_SIZE} YOLO backgrounds.")
    print(f"Saved in: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()
