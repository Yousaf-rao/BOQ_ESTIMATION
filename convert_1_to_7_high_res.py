import os
import cv2
import fitz
import numpy as np
from pathlib import Path

# CONFIG
INPUT_FOLDER = Path("data/input_pdf")
OUTPUT_FOLDER = Path("data/high_res_drawings_no_legend")
ZOOM = 6.0  # High Resolution (around 500-600 DPI)

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def remove_right_legend(img_bgr):
    """
    Main drawing area ko find karta hai aur right side par jo legend block hai
    usko remove kar deta hai.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Invert to find contours
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    
    # Dilate slightly to connect lines
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=3)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_rect = None
    best_area = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        # Main drawing typically takes up at least 20% of the image
        if area > 0.20 * h * w and 0.3 < (cw/ch) < 3.5:
            if area > best_area:
                best_area = area
                best_rect = (x, y, cw, ch)

    if best_rect:
        x, y, cw, ch = best_rect
        pad = 50
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        
        # We ensure we don't go out of bounds
        x2 = min(w, x + cw + pad)
        y2 = min(h, y + ch + pad)
        
        # Extra check: If bounding box still includes the right legend
        # usually right 20% is legend, so if rect touches the right edge, we force crop
        if x2 > w * 0.90:
            x2 = int(w * 0.78)  # Force crop right 22%
            
        print(f"    [CROP] Found main drawing. Cropping to: {cw}x{ch}")
        return img_bgr[y1:y2, x1:x2]
    else:
        # Fallback: Agar contour na mile, to bas right side 22-25% crop kardo (jahan legend hota hai)
        print("    [FALLBACK] Strict bounding box not found. Cropping right 22% manually.")
        x2 = int(w * 0.78)
        return img_bgr[0:h, 0:x2]

def main():
    print(f"Looking for PDFs from 1 to 7 in {INPUT_FOLDER}...\n")
    pdfs = list(INPUT_FOLDER.glob("*.pdf"))
    
    # Bas 1 se 7 wale PDFs ko process karenge aur symbols/drawings ko ignore
    valid_pdfs = []
    for p in pdfs:
        lname = p.name.lower()
        if "symbol" in lname or "drawing.pdf" in lname:
            continue
        valid_pdfs.append(p)
        
    valid_pdfs.sort()
    
    for pdf_path in valid_pdfs:
        print(f"Processing: {pdf_path.name}")
        doc = fitz.open(str(pdf_path))
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # High-Res Convertion
            mat = fitz.Matrix(ZOOM, ZOOM)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            print(f"    [INFO] Resolution converted to high-res: {img_bgr.shape[1]}x{img_bgr.shape[0]}")
            
            # Remove Right Side Legend
            final_img = remove_right_legend(img_bgr)
            
            # Save Output
            name_without_ext = pdf_path.stem.replace(".pdf", "")
            out_name = f"{name_without_ext}_high_res.png"
            out_file = OUTPUT_FOLDER / out_name
            
            cv2.imwrite(str(out_file), final_img)
            print(f"    [COMPLETED] Saved without legend to: {out_file}\n")
            
    print(f"All done! Aapke high-res images '{OUTPUT_FOLDER}' me save ho gaye hain.")

if __name__ == "__main__":
    main()
