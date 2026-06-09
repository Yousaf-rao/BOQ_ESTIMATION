# -*- coding: utf-8 -*-
"""
================================================================
  ORANGE LINE ICON EXTRACTOR
  
  HOW IT WORKS:
    1. Detects orange marker lines you drew on the page
    2. Uses orange lines as separators (top/bottom of each icon)
    3. Crops ONLY left side (icon) - ignores text on right
    4. Saves each icon as clean white PNG to data/icons/
  
  OUTPUT:  page_10_icon_001.png, page_10_icon_002.png ...
  
  USAGE:
    python orange_line_extractor.py
    python orange_line_extractor.py --pages 10 11
    python orange_line_extractor.py --pages 10 --debug
================================================================
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import argparse
import sys

# ======================== PATHS ========================
BASE       = Path(r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project")
PAGES_DIR  = BASE / "data" / "temp_pages"
ICONS_DIR  = BASE / "data" / "icons"

# ==================== ORANGE COLOR =====================
# HSV range for orange marker color
# Hue: 5-25 (orange), Saturation: >150, Value: >150
ORANGE_HUE_LOW  = np.array([5,  140, 140], dtype=np.uint8)
ORANGE_HUE_HIGH = np.array([25, 255, 255], dtype=np.uint8)

# A row is considered "orange line" if this many % of pixels are orange
ORANGE_ROW_THRESHOLD = 0.08   # 8% of row width must be orange

# ==================== ICON CROP ========================
# How much of the left side to keep (icon region - no text)
# Tweak this per page if needed
ICON_FRACTION = {
    8:  0.30,
    9:  0.30,
    10: 0.30,
    11: 0.28,
}
DEFAULT_ICON_FRACTION = 0.30

# Padding inside each orange-bounded slot (pixels to skip near orange line)
ORANGE_INNER_PAD = 8

# Extra horizontal padding around icon
H_PAD = 10

# Output PNG size (square, white background) for model training
OUTPUT_SIZE = (128, 128)

# ======================================================


def load(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(str(path))
    return img


def detect_orange_rows(img_bgr: np.ndarray) -> np.ndarray:
    """
    Returns boolean array of shape (height,) where True = this row
    contains enough orange pixels to be an orange marker line.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, ORANGE_HUE_LOW, ORANGE_HUE_HIGH)

    # Count orange pixels per row
    row_orange = np.sum(mask, axis=1) // 255   # shape: (H,)
    width = img_bgr.shape[1]

    # Boolean: this row is "orange" if threshold met
    is_orange = row_orange > (width * ORANGE_ROW_THRESHOLD)
    return is_orange


def group_orange_bands(is_orange: np.ndarray):
    """
    From boolean row array, find contiguous bands of orange rows.
    Returns list of (y_center) for each orange stripe.
    Also returns list of gaps between stripes as (gap_start, gap_end).
    """
    bands = []
    in_band = False
    band_start = 0

    for y, val in enumerate(is_orange):
        if val and not in_band:
            band_start = y
            in_band = True
        elif not val and in_band:
            bands.append((band_start, y))
            in_band = False

    if in_band:
        bands.append((band_start, len(is_orange)))

    # Gaps between successive orange bands = where icons live
    gaps = []
    for i in range(len(bands) - 1):
        gap_start = bands[i][1]    # end of this orange band
        gap_end   = bands[i+1][0]  # start of next orange band
        if gap_end - gap_start > 10:   # ignore tiny gaps
            gaps.append((gap_start, gap_end))

    return bands, gaps


def extract_icon_from_slot(img_bgr: np.ndarray,
                           y1: int, y2: int,
                           icon_frac: float,
                           inner_pad: int,
                           h_pad: int) -> np.ndarray:
    """
    From the slot between two orange lines (y1:y2),
    crop the LEFT icon region only (no text).
    Returns BGR crop.
    """
    h, w = img_bgr.shape[:2]

    # Vertical: add inner padding (move away from orange lines)
    top    = min(h - 1, y1 + inner_pad)
    bottom = max(0,    y2 - inner_pad)

    if bottom <= top:
        return None

    # Horizontal: only take left 'icon_frac' of page
    icon_right = int(w * icon_frac)

    # Crop the slot+icon strip
    slot = img_bgr[top:bottom, :icon_right].copy()

    # Now find the tight bounding box of the actual drawing (non-white pixels)
    gray = cv2.cvtColor(slot, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Find bounding box of all ink
    coords = cv2.findNonZero(binary)
    if coords is None:
        return None

    rx, ry, rw, rh = cv2.boundingRect(coords)

    # Add padding
    x1 = max(0, rx - h_pad)
    x2 = min(slot.shape[1], rx + rw + h_pad)
    py1 = max(0, ry - h_pad)
    py2 = min(slot.shape[0], ry + rh + h_pad)

    cropped = slot[py1:py2, x1:x2]
    return cropped


def to_png(crop_bgr: np.ndarray, size=(128, 128)) -> Image.Image:
    """Convert BGR crop to white-background RGB PNG, sized for training."""
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    # Resize with aspect ratio preserved
    pil.thumbnail(size, Image.LANCZOS)

    # Center on white square canvas
    canvas = Image.new("RGB", size, (255, 255, 255))
    ox = (size[0] - pil.width)  // 2
    oy = (size[1] - pil.height) // 2
    canvas.paste(pil, (ox, oy))
    return canvas


def save_debug_image(img_bgr, is_orange, bands, gaps, page_num):
    """Save annotated debug image showing orange lines and gaps."""
    vis = img_bgr.copy()
    h, w = vis.shape[:2]
    icon_right = int(w * ICON_FRACTION.get(page_num, DEFAULT_ICON_FRACTION))

    # Shade orange rows red
    for y, val in enumerate(is_orange):
        if val:
            vis[y, :] = (0, 100, 255)

    # Draw green rectangles for each detected gap (icon slot)
    for i, (g1, g2) in enumerate(gaps):
        cv2.rectangle(vis, (0, g1), (icon_right, g2), (0, 255, 0), 2)
        cv2.putText(vis, f"ICON {i+1}", (5, g1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 2)

    # Draw icon boundary line
    cv2.line(vis, (icon_right, 0), (icon_right, h), (255, 200, 0), 2)

    out = ICONS_DIR / f"_debug_orange_p{page_num:02d}.png"
    cv2.imwrite(str(out), vis)
    print(f"  [DEBUG] Saved: {out.name}")


def process_page(page_num: int, debug: bool = False) -> int:
    page_path = PAGES_DIR / f"page_{page_num}.png"
    if not page_path.exists():
        print(f"  [SKIP] page_{page_num}.png not found in {PAGES_DIR}")
        return 0

    print(f"\n{'='*55}")
    print(f"  PAGE {page_num}: {page_path.name}")
    print(f"{'='*55}")

    img = load(page_path)
    h, w = img.shape[:2]
    icon_frac = ICON_FRACTION.get(page_num, DEFAULT_ICON_FRACTION)
    print(f"  Size: {w}x{h}  |  Icon region: left {icon_frac*100:.0f}% ({int(w*icon_frac)}px)")

    # Step 1: Detect orange rows
    is_orange = detect_orange_rows(img)
    orange_count = int(np.sum(is_orange))
    print(f"  Orange rows detected: {orange_count}")

    if orange_count < 2:
        print(f"  [ERROR] Not enough orange lines found! ({orange_count})")
        print(f"          Make sure the image has visible orange marker lines.")
        if debug:
            out = ICONS_DIR / f"_debug_orange_p{page_num:02d}_FAIL.png"
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, ORANGE_HUE_LOW, ORANGE_HUE_HIGH)
            cv2.imwrite(str(out), mask)
            print(f"  [DEBUG] Orange mask saved to: {out.name}")
        return 0

    # Step 2: Group orange rows into bands and find gaps (icon slots)
    bands, gaps = group_orange_bands(is_orange)
    print(f"  Orange stripes: {len(bands)}  ->  Icon slots: {len(gaps)}")

    if debug:
        save_debug_image(img, is_orange, bands, gaps, page_num)

    if not gaps:
        print(f"  [ERROR] No gaps found between orange lines!")
        return 0

    # Step 3: Extract icon from each gap
    saved = 0
    for idx, (g1, g2) in enumerate(gaps):
        crop = extract_icon_from_slot(
            img, g1, g2, icon_frac, ORANGE_INNER_PAD, H_PAD
        )

        if crop is None or crop.shape[0] < 8 or crop.shape[1] < 8:
            print(f"  [SKIP] Slot {idx+1}: empty or too small")
            continue

        icon_png = to_png(crop, OUTPUT_SIZE)

        fname    = f"page_{page_num}_icon_{idx+1:03d}.png"
        out_path = ICONS_DIR / fname
        icon_png.save(out_path, "PNG")
        saved += 1
        print(f"  [OK]   {fname}  "
              f"(y={g1}-{g2}, crop={crop.shape[1]}x{crop.shape[0]})")

    print(f"\n  --> {saved} icons saved for page {page_num}")
    return saved


def main():
    parser = argparse.ArgumentParser(
        description="Extract HVAC icons using orange marker lines as separators"
    )
    parser.add_argument("--pages", nargs="+", type=int,
                        help="Page numbers to process (default: all found)")
    parser.add_argument("--debug", action="store_true",
                        help="Save debug images showing orange detection")
    parser.add_argument("--clean", action="store_true",
                        help="Delete old page_X_icon_*.png before running")
    args = parser.parse_args()

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve pages
    if args.pages:
        page_nums = sorted(args.pages)
    else:
        page_nums = sorted([
            int(f.stem.replace("page_", ""))
            for f in PAGES_DIR.glob("page_*.png")
            if f.stem.replace("page_", "").isdigit()
        ])

    if not page_nums:
        print("[ERROR] No pages found in:", PAGES_DIR)
        sys.exit(1)

    print("\n" + "=" * 55)
    print("  ORANGE LINE ICON EXTRACTOR")
    print("=" * 55)
    print(f"  Pages  : {page_nums}")
    print(f"  Output : {ICONS_DIR}")
    print(f"  Size   : {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]} px (white bg)")
    print("=" * 55)

    if args.clean:
        print("\n[CLEAN] Removing old icon files...")
        for n in page_nums:
            removed = sum(
                1 for f in ICONS_DIR.glob(f"page_{n}_icon_*.png")
                if f.unlink() or True
            )
            if removed:
                print(f"  Removed {removed} files for page_{n}")

    total = 0
    results = []
    for n in page_nums:
        c = process_page(n, debug=args.debug)
        total += c
        results.append((n, c))

    print(f"\n{'='*55}")
    print("  FINAL SUMMARY")
    print(f"{'='*55}")
    for n, c in results:
        tag = "[OK]  " if c > 0 else "[FAIL]"
        print(f"  {tag} page_{n:2d}  -->  {c} icons extracted")
    print(f"\n  TOTAL: {total} icons")
    print(f"  Folder: {ICONS_DIR}")
    print(f"\n  Icons saved as: page_X_icon_001.png, page_X_icon_002.png ...")
    print(f"  >> Rename them yourself with proper symbol names!")
    print("=" * 55)


if __name__ == "__main__":
    main()
