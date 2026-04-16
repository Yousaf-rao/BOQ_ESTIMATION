"""
extract_35_backgrounds.py
=========================
Step 1: PDFs ko Ultra-HD mein convert karo (800 DPI)
Step 2: Har page mein drawing ka main area dhoondo (legend remove karo)
Step 3: Us area se best 640x640 tiles nikaal kar save karo
Goal: data/backgrounds/ mein exactly 35 clean backgrounds
"""

import os
import cv2
import fitz  # PyMuPDF
import numpy as np
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_FOLDER  = Path("data/input_pdf")
OUTPUT_FOLDER = Path("data/backgrounds")
TARGET_COUNT  = 35
TILE_SIZE     = 640     # Final background size for YOLO
ZOOM          = 8.0     # ~800 DPI -- ultra crisp lines
TILES_PER_PAGE = 6      # Har page se max 6 tiles nikaalein
MIN_DENSITY   = 0.008   # Kam se kam itni lines honi chahiye (blank reject)
MAX_DENSITY   = 0.20    # Is se zyada = very dense / legend area (reject)

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ── STEP 0: Old backgrounds saaf karo ─────────────────────────────────────────
old = list(OUTPUT_FOLDER.glob("*.png"))
for f in old:
    f.unlink()
print(f"[CLEAN] Removed {len(old)} old backgrounds.\n")

# ── HELPER: Edge Density ───────────────────────────────────────────────────────
def edge_density(gray_tile):
    blur  = cv2.GaussianBlur(gray_tile, (3, 3), 0)
    edges = cv2.Canny(blur, 40, 120)
    return np.sum(edges > 0) / edges.size

# ── HELPER: Find MAIN DRAWING AREA (removes legend block) ──────────────────────
def find_drawing_area(img_bgr):
    """
    CAD drawings mein ek bada rectangle hota hai jo main floor plan rakhta hai.
    Ye function us bade rectangle ka bounding box return karta hai.
    Agar nahi mila, toh right 22% aur bottom 18% crop kar deta hai (safe fallback).
    """
    h, w = img_bgr.shape[:2]

    gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # Invert (white bg → black bg) taa ke contours milein
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    
    # Dilate to connect nearby lines
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=3)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sabse bada contour = drawing border
    best_rect = None
    best_area = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        # Must be at least 20% of image area and reasonable aspect ratio
        if area > 0.20 * h * w and 0.3 < (cw/ch) < 3.5:
            if area > best_area:
                best_area = area
                best_rect = (x, y, cw, ch)

    if best_rect:
        x, y, cw, ch = best_rect
        # Add a small padding
        pad = 30
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + cw + pad)
        y2 = min(h, y + ch + pad)
        return img_bgr[y1:y2, x1:x2]
    else:
        # Safe fallback: crop right 22% and bottom 18%
        x2 = int(w * 0.78)
        y2 = int(h * 0.82)
        return img_bgr[0:y2, 0:x2]

# ── HELPER: Extract best tiles from drawing area ──────────────────────────────
def extract_tiles(drawing_crop, max_tiles=TILES_PER_PAGE):
    """
    Drawing area ke andar se TILE_SIZE x TILE_SIZE ke best patches nikaalein.
    Medium density wale tiles ko prefer karo (naa bohat khale, naa bohat bhari).
    """
    h, w = drawing_crop.shape[:2]
    if h < TILE_SIZE or w < TILE_SIZE:
        return []
    
    gray = cv2.cvtColor(drawing_crop, cv2.COLOR_BGR2GRAY)
    candidates = []

    stride = int(TILE_SIZE * 0.6)  # 40% overlap
    margin = int(TILE_SIZE * 0.1)
    
    y = margin
    while y + TILE_SIZE <= h - margin:
        x = margin
        while x + TILE_SIZE <= w - margin:
            tile_gray = gray[y:y+TILE_SIZE, x:x+TILE_SIZE]
            d = edge_density(tile_gray)
            if MIN_DENSITY < d < MAX_DENSITY:
                candidates.append((d, y, x))
            x += stride
        y += stride

    if not candidates:
        return []

    # Sort by medium density — avoid extremes
    candidates.sort(key=lambda t: abs(t[0] - 0.04))  # Prefer density near 0.04

    # Select spatially diverse tiles
    selected = []
    min_dist  = TILE_SIZE * 0.5
    for (d, cy, cx) in candidates:
        too_close = any(np.hypot(cx - sx, cy - sy) < min_dist for (_, sy, sx) in selected)
        if not too_close:
            selected.append((d, cy, cx))
        if len(selected) >= max_tiles:
            break

    # Crop and return tiles
    tiles = []
    for (d, y, x) in selected:
        tile = drawing_crop[y:y+TILE_SIZE, x:x+TILE_SIZE]
        tiles.append(tile)
    return tiles

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    pdfs = sorted(INPUT_FOLDER.glob("*.pdf"))
    # Skip HVAC symbols/legend PDFs (they are not floor plans)
    pdfs = [p for p in pdfs if "symbol" not in p.name.lower()
                             and "legend" not in p.name.lower()
                             and "hvac_sym" not in p.name.lower()]

    print(f"[INFO] Found {len(pdfs)} floor plan PDFs to process.\n")
    
    saved = 0
    
    for pdf_path in pdfs:
        if saved >= TARGET_COUNT:
            break
        
        print(f"[PDF] {pdf_path.name}")
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            print(f"  [ERR] Cannot open: {e}")
            continue
        
        for page_num in range(len(doc)):
            if saved >= TARGET_COUNT:
                break
            
            # ── Convert to ultra-HD image ─────────────────────────────────
            page = doc.load_page(page_num)
            mat  = fitz.Matrix(ZOOM, ZOOM)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            
            # PPM buffer → numpy array
            img_np = np.frombuffer(pix.samples, dtype=np.uint8)
            img_np = img_np.reshape((pix.height, pix.width, 3))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            size_mp = (pix.width * pix.height) / 1_000_000
            print(f"  Page {page_num}: {pix.width}x{pix.height} ({size_mp:.1f} MP)")
            
            # ── Find drawing area (remove legend) ─────────────────────────
            drawing_area = find_drawing_area(img_bgr)
            dh, dw = drawing_area.shape[:2]
            print(f"  Drawing area: {dw}x{dh} px")
            
            # Are we working with something big enough?
            if dw < TILE_SIZE * 2 or dh < TILE_SIZE * 2:
                print(f"  [SKIP] Drawing area too small.")
                continue
            
            # ── Extract best tiles ────────────────────────────────────────
            tiles = extract_tiles(drawing_area)
            if not tiles:
                print(f"  [SKIP] No good tiles found in this page.")
                continue
            
            for tile in tiles:
                if saved >= TARGET_COUNT:
                    break
                out_path = OUTPUT_FOLDER / f"real_bg_{saved+1:03d}.png"
                cv2.imwrite(str(out_path), tile)
                print(f"  [SAVED] real_bg_{saved+1:03d}.png")
                saved += 1

    print(f"\n{'='*55}")
    print(f"[DONE] {saved} high-quality backgrounds saved to: {OUTPUT_FOLDER}")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
