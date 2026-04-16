"""
final_bg_extractor.py
=====================
RAM-safe, crash-proof background extractor.
- No DELETE step (safe)
- Zoom=3 (~300 DPI, ~2800x2000 px — manageable)
- Crops right 20% + bottom 15% to remove legend/title
- Extracts 640x640 tiles using Canny edge density
- Saves to data/backgrounds/ as bg_001.png ... bg_035.png
"""

import cv2
import fitz  # PyMuPDF
import numpy as np
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
INPUT_DIR   = Path("data/input_pdf")
OUTPUT_DIR  = Path("data/backgrounds")
TARGET      = 35          # Total backgrounds wanted
ZOOM        = 3.0         # ~300 DPI — fast, clear, RAM-safe
TILE_SZ     = 640         # Output tile size
STRIDE      = 480         # Stride between tiles (overlap ~25%)
MIN_EDGE    = 0.025       # Min edge density — higher = no blank tiles
MAX_EDGE    = 0.18        # Max edge density (reject legend/text-heavy)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Skip symbol/legend PDFs
SKIP_KEYWORDS = ["symbol", "hvac_sym", "legend"]

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def edge_density(gray):
    blur  = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 40, 120)
    return np.sum(edges > 0) / edges.size


def is_uniform(gray):
    """
    Tile ko 4 quadrants mein divide karo.
    Agar koi bhi quadrant bohat zyada blank ho → reject.
    Ye 'half-blank' tiles rokta hai.
    """
    h, w = gray.shape
    mh, mw = h // 2, w // 2
    quads = [
        gray[0:mh, 0:mw],    # Top-left
        gray[0:mh, mw:w],    # Top-right
        gray[mh:h, 0:mw],    # Bottom-left
        gray[mh:h, mw:w],    # Bottom-right
    ]
    for q in quads:
        if edge_density(q) < 0.010:  # Quadrant almost blank → reject whole tile
            return False
    return True


def extract_tiles(img_bgr, max_tiles=6):
    """Extract best 640x640 tiles from the drawing area (legend already removed)."""
    h, w = img_bgr.shape[:2]
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    candidates = []

    y = 0
    while y + TILE_SZ <= h:
        x = 0
        while x + TILE_SZ <= w:
            tile_g = gray[y:y+TILE_SZ, x:x+TILE_SZ]
            d = edge_density(tile_g)
            if MIN_EDGE < d < MAX_EDGE and is_uniform(tile_g):
                candidates.append((d, y, x))
            x += STRIDE
        y += STRIDE

    if not candidates:
        return []

    # Sort by medium density (prefer d near 0.035)
    candidates.sort(key=lambda t: abs(t[0] - 0.035))

    # Spatial diversity filter
    selected = []
    min_dist  = TILE_SZ * 0.5
    for (d, cy, cx) in candidates:
        if all(np.hypot(cx - sx, cy - sy) >= min_dist for (_, sy, sx) in selected):
            selected.append((d, cy, cx))
        if len(selected) >= max_tiles:
            break

    tiles = []
    for (_, y, x) in selected:
        tiles.append(img_bgr[y:y+TILE_SZ, x:x+TILE_SZ])
    return tiles


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    # Find existing count to continue numbering
    existing = sorted(OUTPUT_DIR.glob("bg_*.png"))
    saved    = len(existing)
    print(f"[INFO] Already have {saved} backgrounds. Target = {TARGET}")

    if saved >= TARGET:
        print(f"[OK] Target already met! {saved} backgrounds in {OUTPUT_DIR}")
        return

    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    pdfs = [p for p in pdfs if not any(kw in p.name.lower() for kw in SKIP_KEYWORDS)]
    print(f"[INFO] {len(pdfs)} floor-plan PDFs found.\n")

    for pdf_path in pdfs:
        if saved >= TARGET:
            break

        print(f"[PDF] {pdf_path.name}")
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            print(f"  [ERR] Cannot open: {e}")
            continue

        for page_num in range(len(doc)):
            if saved >= TARGET:
                break

            print(f"  [PAGE {page_num}] Rendering at {ZOOM}x zoom...")
            try:
                page   = doc.load_page(page_num)
                mat    = fitz.Matrix(ZOOM, ZOOM)
                pix    = page.get_pixmap(matrix=mat, alpha=False)

                # Build numpy array without PIL
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, 3)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                print(f"         Size: {pix.width}x{pix.height} px")

                # ── Crop out legend (right 20%, bottom 15%) ──────────────
                h, w    = img_bgr.shape[:2]
                crop_w  = int(w * 0.80)
                crop_h  = int(h * 0.85)
                drawing = img_bgr[0:crop_h, 0:crop_w]
                print(f"         Drawing area: {crop_w}x{crop_h}")

                # ── Extract tiles ─────────────────────────────────────────
                tiles = extract_tiles(drawing, max_tiles=7)
                print(f"         Tiles found: {len(tiles)}")

                for tile in tiles:
                    if saved >= TARGET:
                        break
                    saved += 1
                    out_path = OUTPUT_DIR / f"bg_{saved:03d}.png"
                    cv2.imwrite(str(out_path), tile)
                    print(f"         [SAVED] bg_{saved:03d}.png")

            except Exception as e:
                print(f"  [ERR] Page {page_num}: {e}")
                continue

    print(f"\n{'='*50}")
    print(f"[DONE] {saved} backgrounds in {OUTPUT_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
