#!/usr/bin/env python3
"""
Red-Annotated Screenshot Extractor - Intelligent Region Split
Uses the drawn red horizontal lines to perfectly separate the image vertically into 6 boxes!
"""

import cv2
import numpy as np
from pathlib import Path
import os
from scipy.signal import find_peaks

class RedScreenshotExtractor:
    def __init__(self, image_path, output_dir, symbol_names):
        self.image_path = Path(image_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.symbol_names = symbol_names
        
    def extract(self):
        print(f"🔍 Processing Annotated Screenshot: {self.image_path.name}")
        
        # Load image
        img = cv2.imread(str(self.image_path))
        if img is None:
            raise ValueError(f"Could not load image at {self.image_path}")
            
        height, width = img.shape[:2]
        
        # Find Red lines using HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Red ranges in HSV
        mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Dilate red mask to completely capture red lines
        kernel = np.ones((5,5), np.uint8)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        
        # Remove red from the original image (make it white)
        clean_img = img.copy()
        clean_img[red_mask > 0] = [255, 255, 255]
        
        # 1. FIND THE RED SEPARATOR Y-COORDINATES
        h_proj_red = np.sum(red_mask, axis=1)
        
        # Find peaks in the horizontal projection of red pixels!
        # distance=30 ensures we only detect one peak per drawn line (in case they are thick)
        peaks, _ = find_peaks(h_proj_red, height=np.max(h_proj_red)*0.1, distance=30)
        
        # Include top and bottom boundaries just in case red line was cropped out
        if len(peaks) > 0 and peaks[0] > 50:
            peaks = np.insert(peaks, 0, 0)
        if len(peaks) > 0 and peaks[-1] < height - 50:
            peaks = np.append(peaks, height)
            
        print(f"Detected Y-split coordinates across red lines: {peaks}")
        
        # Convert to grayscale for padding calculation
        gray = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # The numbers 1-6 are on the far left. We crop them out completely to find symbol bounds.
        safe_left_crop = int(width * 0.15)
        
        saved = 0
        debug_viz = img.copy()
        
        # We loop through consecutive peaks which form our rows
        num_expected = len(self.symbol_names)
        
        for i in range(len(peaks) - 1):
            if i >= num_expected:
                break
                
            y_start = peaks[i]
            y_end = peaks[i+1]
            
            # Extract Region
            row_bin = binary[y_start:y_end, safe_left_crop:]
            y_coords, x_coords = np.where(row_bin > 0)
            
            if len(x_coords) == 0:
                print(f"⚠️ Gap {i+1} is empty!")
                continue
                
            x1 = x_coords.min() + safe_left_crop
            x2 = x_coords.max() + safe_left_crop
            y1 = y_start + y_coords.min()
            y2 = y_start + y_coords.max()
            
            # PADDING
            pad_x = 60
            pad_y = 50
            
            px1 = max(0, x1 - pad_x)
            py1 = max(0, y1 - pad_y)
            px2 = min(width, x2 + pad_x) 
            py2 = min(height, y2 + pad_y)
            
            # Crop the symbol from clean image (without red lines)
            symbol_img = clean_img[py1:py2, px1:px2].copy()
            
            symbol_rgba = self.make_transparent(symbol_img)
            name = self.symbol_names[i]
            
            out_path = self.output_dir / f"{name}.png"
            cv2.imwrite(str(out_path), symbol_rgba)
            print(f"✅ Extracted Row {i+1} -> {name}.png")
            
            # Draw green box on debug visualization
            cv2.rectangle(debug_viz, (px1, py1), (px2, py2), (0, 255, 0), 3)
            saved += 1
            
        print(f"🎉 Done! Extracted {saved} symbols.")
        cv2.imwrite(str(self.output_dir / "_debug_red_boxes.png"), debug_viz)
        
    def make_transparent(self, img):
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        _, alpha = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        if len(img.shape) == 3:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            r, g, b = cv2.split(rgb)
        else:
            r = g = b = img
        return cv2.merge([r, g, b, alpha])

if __name__ == "__main__":
    # Uploaded image path
    SCREENSHOT_PATH = r"C:\Users\Friends shop\.gemini\antigravity\brain\f7ec32ba-9d7c-4db0-8edc-2e6be2481c40\media__1775822868060.png"
    
    # Save directly to main icons folder
    OUTPUT_FOLDER = r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project\data\icons"
    
    # The 6 symbols
    VALVE_NAMES = [
        "page_15_01_gate_valve_threaded",
        "page_15_02_globe_valve_threaded",
        "page_15_03_gate_valve_hose",
        "page_15_04_check_valve",
        "page_15_05_wye_strainer_ball_valve",
        "page_15_06_wye_strainer_drain"
    ]
    
    if os.path.exists(SCREENSHOT_PATH):
        extractor = RedScreenshotExtractor(SCREENSHOT_PATH, OUTPUT_FOLDER, VALVE_NAMES)
        extractor.extract()
    else:
        print(f"File not found: {SCREENSHOT_PATH}")
