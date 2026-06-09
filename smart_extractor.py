"""
smart_extractor.py
------------------
User's Smart Logic implemented with PyMuPDF (to avoid Windows Poppler issues).
1. PDF to High-Res Image (DPI 300 equivalent)
2. Auto-Cropping (Right 18%, Bottom 15%)
3. Canny Edge Density Filter (0.01 to 0.15)
"""

import os
import cv2
import fitz  # PyMuPDF instead of pdf2image
import numpy as np
from PIL import Image

# Configuration
INPUT_FOLDER = 'data/input_pdf'
OUTPUT_FOLDER = 'data/backgrounds'
TARGET_COUNT = 35

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Clear old junk
for old_bg in os.listdir(OUTPUT_FOLDER):
    try:
        os.remove(os.path.join(OUTPUT_FOLDER, old_bg))
    except:
        pass

def is_good_drawing(img_np):
    """Check karta hai ke image drawing hai ya sirf khali safa ya text"""
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
    
    # Bohat kam lines = Khali page (Skip)
    # Bohat zyada lines = Legend ya Text heavy (Skip)
    print(f"      [Density Check] {edge_density:.4f}")
    return 0.01 < edge_density < 0.15

def smart_crop_legend(pil_img):
    """Legend aksar right ya bottom block mein hota hai, usay katna"""
    width, height = pil_img.size
    # 82% width, 85% height
    crop_width = int(width * 0.82)
    crop_height = int(height * 0.85)
    return pil_img.crop((0, 0, crop_width, crop_height))

def process_and_filter():
    pdf_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.pdf')]
    saved_count = 0
    
    print(f"Checking {len(pdf_files)} PDFs...\n")

    for pdf in pdf_files:
        if saved_count >= TARGET_COUNT: break
        
        path = os.path.join(INPUT_FOLDER, pdf)
        try:
            print(f"Opening: {pdf}")
            doc = fitz.open(path)
            
            for i in range(len(doc)):
                # Convert PDF page to high-res Image (zoom 4 ≈ 300 DPI)
                page = doc.load_page(i)
                mat = fitz.Matrix(4.0, 4.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                img_data = pix.tobytes("ppm")
                pil_page = Image.frombytes("RGB", [pix.width, pix.height], img_data)
                
                # 1. Smart Crop (Legend removal)
                cropped_page = smart_crop_legend(pil_page)
                
                # 2. Convert to OpenCV format for analysis
                img_np = cv2.cvtColor(np.array(cropped_page), cv2.COLOR_RGB2BGR)
                
                # 3. Quality Check
                if is_good_drawing(img_np):
                    save_name = f"bg_{saved_count:03d}.png"
                    cv2.imwrite(os.path.join(OUTPUT_FOLDER, save_name), img_np)
                    saved_count += 1
                    print(f"  --> Sahi Drawing Mili: {save_name}")
                    
                    if saved_count >= TARGET_COUNT: break
                else:
                    print(f"  --> Skipped: {pdf} Page {i} (Acha background nahi lag raha)")
                    
        except Exception as e:
            print(f"Error processing {pdf}: {e}")

    print(f"\n[DONE] Total {saved_count} SMART images '{OUTPUT_FOLDER}' mein save hain.")

if __name__ == "__main__":
    process_and_filter()
