# -*- coding: utf-8 -*-
"""
================================================================
  HVAC ICON EXTRACTOR - DUAL MODE
  
  MODE 1 (SCREENSHOT): If you provide a screenshot with orange 
          marker lines, it detects those lines as separators.
          
  MODE 2 (AUTO): If no screenshot given, works on original PDF 
          page and auto-detects symbol rows using projection.
  
  OUTPUT: data/icons/page_10_icon_001.png, _002.png ...
         (Clean white background, 128x128 px for model training)
  
  USAGE:
    # Mode 2 - Auto detect from original page (NO screenshot needed)
    python final_icon_extractor.py --pages 10

    # Mode 1 - Use YOUR marked screenshot 
    python final_icon_extractor.py --screenshot path\to\screenshot.png --page 10
    
    # Process all pages auto mode
    python final_icon_extractor.py --all
    
    # See debug images
    python final_icon_extractor.py --pages 10 --debug
================================================================
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import argparse
import sys

# ======================== PATHS ========================
BASE      = Path(r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project")
PAGES_DIR = BASE / "data" / "temp_pages"
ICONS_DIR = BASE / "data" / "icons"

# =================== OUTPUT SETTINGS ===================
OUTPUT_SIZE  = (128, 128)   # Final icon size (square, white background)
BORDER_PAD   = 12           # Pixels of white border around each icon

# ======= ICON COLUMN: How much left% is the symbol area =======
# Right side is always text - we don't want that
PAGE_ICON_COL = {
    6:  0.45,   # Ductwork page 1
    7:  0.45,   # Ductwork page 2 (FSD, ACD etc)
    8:  0.35,   # Ductwork symbols (FC, elbow...)
    9:  0.35,   # More ductwork
    10: 0.30,   # Terminal unit symbols
    11: 0.25,   # Air terminal symbols
    12: 0.28,   # Piping line symbols
    13: 0.28,   # More piping and hanger line symbols
}
DEFAULT_COL = 0.35

# Extra pixels added to icon column to prevent symbol cutoff at the boundary
ICON_EXTRA_PIXELS = 200

# ======= ORANGE DETECTION (Mode 1) =======
ORANGE_LOW  = np.array([5,  130, 130], dtype=np.uint8)   # HSV lower bound
ORANGE_HIGH = np.array([30, 255, 255], dtype=np.uint8)   # HSV upper bound
ORANGE_ROW_FRACTION = 0.05   # 5% of row width must be orange

# ======= AUTO ROW DETECTION (Mode 2) =======
# For auto mode: gaps between symbol rows
# IMPORTANT: keep MIN_GAP small so closely-spaced symbols are split correctly
AUTO_MIN_GAP    = 15    # rows of white space = new symbol starts
AUTO_MIN_HEIGHT = 18    # minimum row height in pixels to be a valid symbol
# ======================================================

# ======= MANUAL BAND OVERRIDES =======
# When auto-detection fails (merges/splits symbols), hard-code exact y-coords.
# Format: page_num -> list of (y_start, y_end) in pixels (at 2550x3300 resolution)
# - Skip title rows and logo rows by simply NOT including them.
# - Split merged symbols into two separate tuples.
# - Merge split symbols into one wider tuple.
PAGE_MANUAL_BANDS = {
    10: [
        #  y1    y2    Symbol name
        (  251,  358), # CON_REC  - Convector/Radiator Recessed
        (  450,  580), # CON_WH   - Convector/Radiator Wall Hung
        (  619,  811), # FCU_REC  - Floor FCU Vertical Recessed
        (  826,  980), # FCU_CAB  - Floor FCU Vertical Cabinet  (split from merged)
        (  980, 1147), # TWU      - Thru Wall AC Unit           (split from merged)
        ( 1163, 1292), # PTAC_WIN - Window Type AC (PTAC)
        ( 1319, 1525), # HP       - Floor Mounted Heat Pump
        ( 1581, 1791), # HP2      - Heat Pump band 2
        ( 1856, 1944), # AC_CUR   - Air Curtain
        ( 2021, 2136), # UH_HOR   - Unit Heater Horizontal
        ( 2180, 2480), # UH_VER   - Unit Heater Vertical (merged: was split)
        ( 2496, 2607), # RCP_22   - 2x2 Radiant Ceiling Panel
        ( 2692, 2802), # RCP_24   - 2x4 Radiant Ceiling Panel
        # intentionally skipping: 125-195 (title) and 2859-3044 (logo)
    ],
}
# ======================================


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Cannot open: {path}")
    return img


def get_icon_strip(img: np.ndarray, page_num: int) -> np.ndarray:
    """Return only the left 'icon column' of the image."""
    frac = PAGE_ICON_COL.get(page_num, DEFAULT_COL)
    w = img.shape[1]
    return img[:, : int(w * frac)].copy(), frac


# ─────────────── MODE 1: ORANGE LINES ────────────────────────────

def find_orange_separators(img_bgr: np.ndarray):
    """
    Detect horizontal orange marker lines.
    Returns list of (y_start, y_end) for each orange stripe.
    """
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, ORANGE_LOW, ORANGE_HIGH)

    row_orange = np.sum(mask, axis=1) // 255
    width      = img_bgr.shape[1]
    is_orange  = row_orange > (width * ORANGE_ROW_FRACTION)

    # Group consecutive orange rows
    bands = []
    in_b  = False
    bs    = 0
    for y, val in enumerate(is_orange):
        if val and not in_b:
            bs = y;  in_b = True
        elif not val and in_b:
            bands.append((bs, y));  in_b = False
    if in_b:
        bands.append((bs, len(is_orange)))

    return bands


def gaps_from_bands(bands, img_height: int):
    """Return (y1, y2) gaps between successive orange bands."""
    gaps = []
    for i in range(len(bands) - 1):
        g1 = bands[i][1]        # end of orange stripe
        g2 = bands[i+1][0]      # start of next orange stripe
        if g2 - g1 > 15:
            gaps.append((g1, g2))
    return gaps


# ─────────────── MODE 2: AUTO PROJECTION ─────────────────────────

def find_symbol_rows_auto(strip: np.ndarray, min_gap: int, min_h: int):
    """
    Scan the binary image column by column (horizontal projection).
    Returns list of (y_start, y_end) for each symbol row.
    """
    gray   = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    blur   = cv2.GaussianBlur(gray, (3, 3), 0)
    _, bin_img = cv2.threshold(blur, 0, 255,
                               cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Clean noise
    kern   = np.ones((3, 3), np.uint8)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN,  kern, iterations=1)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kern, iterations=2)

    row_ink = np.sum(bin_img, axis=1) // 255

    bands   = []
    in_band = False
    gap_cnt = 0
    b_start = 0

    for y, count in enumerate(row_ink):
        if count > 3:
            if not in_band:
                b_start = y
                in_band = True
            gap_cnt = 0
        else:
            if in_band:
                gap_cnt += 1
                if gap_cnt >= min_gap:
                    y_end = y - gap_cnt + 1
                    if y_end - b_start >= min_h:
                        bands.append((b_start, y_end))
                    in_band = False
                    gap_cnt = 0

    if in_band:
        y_end = len(row_ink)
        if y_end - b_start >= min_h:
            bands.append((b_start, y_end))

    return bands


# ─────────────── COMMON: CROP + SAVE ─────────────────────────────

def tight_crop(strip_bgr: np.ndarray, y1: int, y2: int,
               pad: int = 12) -> np.ndarray:
    """
    Within the row band (y1:y2), tightly crop the actual ink,
    then add white padding around it.
    """
    h, w = strip_bgr.shape[:2]
    slot  = strip_bgr[y1:y2, :]

    gray  = cv2.cvtColor(slot, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    pts   = cv2.findNonZero(bw)
    if pts is None:
        return None

    rx, ry, rw, rh = cv2.boundingRect(pts)

    # Apply pad
    x1p = max(0, rx      - pad)
    x2p = min(w, rx + rw + pad)
    y1p = max(0, ry      - pad)
    y2p = min(slot.shape[0], ry + rh + pad)

    return slot[y1p:y2p, x1p:x2p].copy()


def to_white_png(crop_bgr: np.ndarray, size=(128, 128)) -> Image.Image:
    """Convert BGR crop to white-background square PNG."""
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    # Scale keeping aspect ratio
    pil.thumbnail(size, Image.LANCZOS)

    # Centre on white canvas
    canvas = Image.new("RGB", size, (255, 255, 255))
    ox     = (size[0] - pil.width)  // 2
    oy     = (size[1] - pil.height) // 2
    canvas.paste(pil, (ox, oy))
    return canvas


def save_debug(img_bgr, bands, frac, page_num, mode_label):
    """Save annotated image to icons/ for inspection."""
    vis   = img_bgr.copy()
    h, w  = vis.shape[:2]
    x_cut = int(w * frac) + ICON_EXTRA_PIXELS

    colors = [(0,220,0),(255,80,0),(0,80,255),(200,0,200),(0,200,200)]

    for i, (y1, y2) in enumerate(bands):
        col = colors[i % len(colors)]
        cv2.rectangle(vis, (0, y1), (x_cut, y2), col, 3)
        cv2.putText(vis, f"#{i+1}", (6, y1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)

    # Yellow vertical line showing icon boundary
    cv2.line(vis, (x_cut, 0), (x_cut, h), (0, 220, 255), 3)

    out = ICONS_DIR / f"_debug_p{page_num:02d}_{mode_label}.png"
    cv2.imwrite(str(out), vis)
    print(f"  [DEBUG] {out.name}")


# ─────────────── MAIN PAGE PROCESSOR ─────────────────────────────

def process_page(page_num: int, screenshot_path: Path = None,
                 debug: bool = False) -> int:
    """
    Process one legend page and extract all icons.
    If screenshot_path given, uses orange-line mode.
    Otherwise uses auto-detection mode.
    Returns number of icons saved.
    """
    print(f"\n{'='*58}")
    print(f"  PAGE {page_num}")
    print(f"{'='*58}")

    # --- Load image ---
    if screenshot_path and screenshot_path.exists():
        img = load_image(screenshot_path)
        mode = "SCREENSHOT (orange lines)"
    else:
        page_path = PAGES_DIR / f"page_{page_num}.png"
        if not page_path.exists():
            print(f"  [SKIP] page_{page_num}.png not found")
            return 0
        img = load_image(page_path)
        mode = "AUTO (projection)"

    h, w = img.shape[:2]
    frac = PAGE_ICON_COL.get(page_num, DEFAULT_COL)
    print(f"  Mode   : {mode}")
    print(f"  Image  : {w} x {h} px")
    print(f"  Icon % : left {frac*100:.0f}%  ({int(w*frac)} px)")

    # --- Get icon strip ---
    strip_bgr = img[:, : int(w * frac) + ICON_EXTRA_PIXELS].copy()

    # --- Find symbol rows ---
    if page_num in PAGE_MANUAL_BANDS:
        # MODE 0: MANUAL override - exact y-coords (most accurate)
        bands = PAGE_MANUAL_BANDS[page_num]
        mode_label = "MANUAL"
        print(f"  Mode   : MANUAL OVERRIDE (hard-coded y-coords)")
    elif screenshot_path and screenshot_path.exists():
        # MODE 1: orange lines on the full image
        orange_bands = find_orange_separators(img)
        print(f"  Orange stripes found: {len(orange_bands)}")
        if len(orange_bands) < 2:
            print(f"  [WARN] Not enough orange lines ({len(orange_bands)})!")
            print(f"         Falling back to AUTO mode...")
            bands = find_symbol_rows_auto(strip_bgr, AUTO_MIN_GAP, AUTO_MIN_HEIGHT)
            mode_label = "AUTO_fallback"
        else:
            bands = gaps_from_bands(orange_bands, h)
            mode_label = "ORANGE"
    else:
        # MODE 2: auto projection
        bands = find_symbol_rows_auto(strip_bgr, AUTO_MIN_GAP, AUTO_MIN_HEIGHT)
        mode_label = "AUTO"

    print(f"  Bands found: {len(bands)}")

    if not bands:
        print(f"  [ERROR] Zero symbol rows detected!")
        return 0

    if debug:
        save_debug(img, bands, frac, page_num, mode_label)

    # --- Crop + Save ---
    saved = 0
    for idx, (y1, y2) in enumerate(bands):
        # Add inner padding if orange mode (move away from the orange line)
        if mode_label == "ORANGE":
            y1 = min(img.shape[0]-1, y1 + 5)
            y2 = max(0,             y2 - 5)

        crop = tight_crop(strip_bgr, y1, y2, pad=BORDER_PAD)

        if crop is None or crop.shape[0] < 8 or crop.shape[1] < 8:
            print(f"  [SKIP] Band {idx+1}: empty")
            continue

        if page_num in (12, 13, 14, 15, 16, 17, 18):
            # Piping lines are very wide; saving them as 128x128 destroys text pixels. Keep original size.
            icon = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        else:
            icon = to_white_png(crop, OUTPUT_SIZE)

        fname    = f"page_{page_num}_icon_{idx+1:03d}.png"
        out_path = ICONS_DIR / fname
        icon.save(out_path, "PNG")
        saved += 1
        print(f"  [SAVED] {fname}  "
              f"[ y:{y1}-{y2} | crop:{crop.shape[1]}x{crop.shape[0]} ]")

    print(f"  --> Total: {saved} icons saved")
    return saved


# ─────────────────────────── ENTRY ───────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="HVAC Icon Extractor - orange lines or auto mode"
    )
    parser.add_argument("--pages", nargs="+", type=int,
                        help="Page numbers to extract from (e.g. --pages 8 9 10 11)")
    parser.add_argument("--all",   action="store_true",
                        help="Process ALL pages found in temp_pages/")
    parser.add_argument("--screenshot", type=str,
                        help="Path to screenshot WITH orange lines "
                             "(use with --page for single page)")
    parser.add_argument("--page",  type=int,
                        help="Single page number (used with --screenshot)")
    parser.add_argument("--debug", action="store_true",
                        help="Save debug images showing detected bands")
    parser.add_argument("--clean", action="store_true",
                        help="Delete existing page_X_icon_*.png files first")
    args = parser.parse_args()

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    # Determine pages
    if args.all:
        page_nums = sorted([
            int(f.stem.replace("page_", ""))
            for f in PAGES_DIR.glob("page_*.png")
            if f.stem.replace("page_", "").isdigit()
        ])
    elif args.pages:
        page_nums = sorted(args.pages)
    elif args.page:
        page_nums = [args.page]
    else:
        # Default: process pages 6-11 (HVAC legend pages)
        page_nums = [p for p in range(6, 12)
                     if (PAGES_DIR / f"page_{p}.png").exists()]

    if not page_nums:
        print("[ERROR] No pages found! Use --pages or --all")
        sys.exit(1)

    screenshot = Path(args.screenshot) if args.screenshot else None

    print("\n" + "=" * 58)
    print("  HVAC ICON EXTRACTOR")
    print("=" * 58)
    print(f"  Pages  : {page_nums}")
    print(f"  Mode   : {'SCREENSHOT' if screenshot else 'AUTO DETECT'}")
    print(f"  Output : {ICONS_DIR}")
    print(f"  Size   : {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]} white PNG")
    print("=" * 58)

    # Clean old files
    if args.clean:
        print("\n[CLEAN] Removing old icon files...")
        for n in page_nums:
            cnt = 0
            for f in ICONS_DIR.glob(f"page_{n}_icon_*.png"):
                f.unlink()
                cnt += 1
            if cnt:
                print(f"  Removed {cnt} files for page_{n}")

    # Run
    total   = 0
    results = []
    for n in page_nums:
        ss = screenshot if (args.page and args.page == n) else None
        c  = process_page(n, screenshot_path=ss, debug=args.debug)
        total += c
        results.append((n, c))

    # Summary
    print(f"\n{'='*58}")
    print("  FINAL SUMMARY")
    print(f"{'='*58}")
    for n, c in results:
        tag = "[OK]  " if c > 0 else "[ZERO]"
        print(f"  {tag}  page_{n:2d}  -->  {c} icons")
    print(f"\n  TOTAL ICONS SAVED : {total}")
    print(f"  SAVED IN          : {ICONS_DIR}")
    print(f"\n  Rename icons with proper names (FCU_REC, MVD, FSD etc)")
    print("=" * 58)


if __name__ == "__main__":
    main()
