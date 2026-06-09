#!/usr/bin/env python3
"""
Advanced Symbol Extractor - Optimized for ALL Pages including Piping (12, 13)
Handles horizontal line symbols, small components, and text-like shapes
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
from pathlib import Path
from typing import List, Dict, Tuple
import json

class UniversalSymbolExtractor:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Page-specific configurations
        self.page_configs = {
            # Piping pages - need special handling for horizontal lines
            'page_12': {
                'left_percent': 0.55,  # Wider crop for long lines
                'min_size': (30, 15),   # Smaller height for horizontal lines
                'max_size_factor': (0.95, 0.3),  # Allow wider, shorter
                'aspect_range': (0.05, 15.0),    # Very flat to very tall
                'morph_kernel': (3, 7),          # Wider kernel for horizontal
                'text_filter': False               # Don't filter text-like
            },
            'page_13': {
                'left_percent': 0.55,
                'min_size': (30, 15),
                'max_size_factor': (0.95, 0.3),
                'aspect_range': (0.05, 15.0),
                'morph_kernel': (3, 7),
                'text_filter': False
            },
            # Default for other pages
            'default': {
                'left_percent': 0.45,
                'min_size': (50, 50),
                'max_size_factor': (0.9, 0.5),
                'aspect_range': (0.15, 5.0),
                'morph_kernel': (5, 5),
                'text_filter': True
            }
        }
        
    def get_page_config(self, page_name: str) -> Dict:
        """Get configuration for specific page"""
        for page_key in self.page_configs.keys():
            if page_key in page_name.lower():
                return self.page_configs[page_key]
        return self.page_configs['default']
    
    def extract_left_region(self, image_path: Path, config: Dict) -> np.ndarray:
        """Extract left portion based on page config"""
        img = Image.open(image_path)
        width, height = img.size
        
        left = 0
        top = 0
        right = int(width * config['left_percent'])
        bottom = height
        
        cropped = img.crop((left, top, right, bottom))
        img_array = np.array(cropped)
        
        # Convert to BGR for OpenCV
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    def preprocess_for_extraction(self, img_array: np.ndarray, config: Dict) -> np.ndarray:
        """
        Advanced preprocessing to handle different symbol types
        """
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array
        
        # Invert: symbols become white (255), background black (0)
        # Use adaptive thresholding for better results
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21,  # Block size
            10   # C constant
        )
        
        # Also try Otsu for comparison
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Combine both
        combined = cv2.bitwise_or(binary, otsu)
        
        # Morphological operations with page-specific kernel
        kernel_size = config['morph_kernel']
        kernel = np.ones(kernel_size, np.uint8)
        
        # Close gaps in symbols
        processed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Remove small noise
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), iterations=1)
        
        return processed
    
    def find_symbols_connected_components(self, binary_img: np.ndarray, 
                                         original_img: np.ndarray,
                                         config: Dict) -> List[Dict]:
        """
        Find symbols using connected components with relaxed constraints
        """
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary_img, connectivity=8
        )
        
        height, width = binary_img.shape
        symbols = []
        
        min_w, min_h = config['min_size']
        max_w_factor, max_h_factor = config['max_size_factor']
        
        for i in range(1, num_labels):  # Skip background
            x, y, w, h, area = stats[i]
            
            # Size checks
            if w < min_w or h < min_h:
                continue
            if w > width * max_w_factor or h > height * max_h_factor:
                continue
            
            # Aspect ratio check
            aspect = w / h if h > 0 else 0
            min_aspect, max_aspect = config['aspect_range']
            if not (min_aspect < aspect < max_aspect):
                continue
            
            # Minimum area check (filter tiny noise)
            if area < 200:
                continue
            
            # Extract symbol with padding
            padding = 20
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(width, x + w + padding)
            y2 = min(height, y + h + padding)
            
            symbol_img = original_img[y1:y2, x1:x2].copy()
            
            # Create clean transparent version
            symbol_clean = self.make_transparent_background(symbol_img)
            
            symbols.append({
                'image': symbol_clean,
                'bbox': (x1, y1, x2, y2),
                'center': centroids[i],
                'area': area,
                'aspect': aspect,
                'page_config': config
            })
        
        # Sort by vertical position (top to bottom)
        symbols.sort(key=lambda s: s['bbox'][1])
        return symbols
    
    def find_symbols_contours(self, binary_img: np.ndarray, 
                             original_img: np.ndarray,
                             config: Dict) -> List[Dict]:
        """
        Alternative: Find symbols using contours (better for some shapes)
        """
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        height, width = binary_img.shape
        symbols = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200:  # Too small
                continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Size checks
            min_w, min_h = config['min_size']
            max_w_factor, max_h_factor = config['max_size_factor']
            
            if w < min_w or h < min_h:
                continue
            if w > width * max_w_factor or h > height * max_h_factor:
                continue
            
            # Aspect ratio
            aspect = w / h if h > 0 else 0
            min_aspect, max_aspect = config['aspect_range']
            if not (min_aspect < aspect < max_aspect):
                continue
            
            # Extract with padding
            padding = 20
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(width, x + w + padding)
            y2 = min(height, y + h + padding)
            
            symbol_img = original_img[y1:y2, x1:x2].copy()
            symbol_clean = self.make_transparent_background(symbol_img)
            
            symbols.append({
                'image': symbol_clean,
                'bbox': (x1, y1, x2, y2),
                'area': area,
                'aspect': aspect
            })
        
        symbols.sort(key=lambda s: s['bbox'][1])
        return symbols
    
    def make_transparent_background(self, symbol_img: np.ndarray) -> Image.Image:
        """
        Convert symbol to RGBA with transparent background
        """
        if len(symbol_img.shape) == 3:
            # Convert to grayscale for alpha mask
            gray = cv2.cvtColor(symbol_img, cv2.COLOR_BGR2GRAY)
            
            # Create alpha: dark pixels = opaque, light = transparent
            # Invert because symbols are dark on light background
            _, alpha = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            
            # Convert BGR to RGB
            rgb = cv2.cvtColor(symbol_img, cv2.COLOR_BGR2RGB)
            
            # Create RGBA
            r, g, b = cv2.split(rgb)
            rgba = cv2.merge([r, g, b, alpha])
            
        else:
            # Already grayscale
            _, alpha = cv2.threshold(symbol_img, 240, 255, cv2.THRESH_BINARY_INV)
            rgba = cv2.cvtColor(symbol_img, cv2.COLOR_GRAY2RGBA)
            rgba[:, :, 3] = alpha
        
        # Convert to PIL
        pil_img = Image.fromarray(rgba)
        
        # Optional: Trim transparent borders
        bbox = pil_img.getbbox()
        if bbox:
            pil_img = pil_img.crop(bbox)
            # Add small padding back
            w, h = pil_img.size
            padded = Image.new('RGBA', (w+20, h+20), (255, 255, 255, 0))
            padded.paste(pil_img, (10, 10))
            pil_img = padded
        
        return pil_img
    
    def merge_close_symbols(self, symbols: List[Dict], merge_distance: int = 50) -> List[Dict]:
        """
        Merge symbols that are very close (might be parts of same symbol)
        """
        if len(symbols) < 2:
            return symbols
        
        merged = []
        used = set()
        
        for i, sym1 in enumerate(symbols):
            if i in used:
                continue
            
            # Find close symbols
            group = [sym1]
            x1, y1, x2, y2 = sym1['bbox']
            cx1, cy1 = (x1+x2)/2, (y1+y2)/2
            
            for j, sym2 in enumerate(symbols[i+1:], i+1):
                if j in used:
                    continue
                
                x3, y3, x4, y4 = sym2['bbox']
                cx2, cy2 = (x3+x4)/2, (y3+y4)/2
                
                distance = np.sqrt((cx1-cx2)**2 + (cy1-cy2)**2)
                
                if distance < merge_distance:
                    group.append(sym2)
                    used.add(j)
            
            # Merge group if needed
            if len(group) > 1:
                # Combine bounding boxes
                all_x = [s['bbox'][0] for s in group] + [s['bbox'][2] for s in group]
                all_y = [s['bbox'][1] for s in group] + [s['bbox'][3] for s in group]
                
                merged_bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
                
                # Extract from original image (need to reload or store original)
                # For now, use largest symbol
                largest = max(group, key=lambda s: s['area'])
                merged.append(largest)
            else:
                merged.append(sym1)
            
            used.add(i)
        
        return merged
    
    def save_visualization(self, original_img: np.ndarray, 
                          symbols: List[Dict], 
                          output_path: Path):
        """
        Save debug image showing detected symbols
        """
        vis_img = original_img.copy()
        
        for i, sym in enumerate(symbols):
            x1, y1, x2, y2 = sym['bbox']
            color = (0, 255, 0) if i % 2 == 0 else (255, 0, 0)
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis_img, f"{i+1}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        cv2.imwrite(str(output_path), vis_img)
    
    def process_single_page(self, image_file: Path) -> Dict:
        """Process one page with appropriate configuration"""
        page_name = image_file.stem
        config = self.get_page_config(page_name)
        
        print(f"\n📄 Processing: {page_name}")
        print(f"   Config: {config['left_percent']*100:.0f}% width, "
              f"min_size={config['min_size']}, aspect={config['aspect_range']}")
        
        # Extract region
        left_img = self.extract_left_region(image_file, config)
        
        # Preprocess
        binary = self.preprocess_for_extraction(left_img, config)
        
        # Try both methods and combine
        symbols_cc = self.find_symbols_connected_components(binary, left_img, config)
        symbols_ct = self.find_symbols_contours(binary, left_img, config)
        
        # Use method with more detections (usually connected components is better)
        symbols = symbols_cc if len(symbols_cc) >= len(symbols_ct) else symbols_ct
        
        # Special handling for piping pages
        if 'page_12' in page_name or 'page_13' in page_name:
            # Don't filter "text-like" - piping symbols ARE horizontal lines
            print(f"   🔧 Piping page detected - {len(symbols)} raw symbols found")
        else:
            # Filter for other pages
            symbols = [s for s in symbols if 0.2 < s['aspect'] < 4.0 or s['area'] > 1000]
        
        if not symbols:
            print(f"   ⚠️ No symbols found!")
            return {'page': page_name, 'count': 0}
        
        # Modify this part to save files FLAT in icons directory
        # so that auto-rename script can find them.
        saved = 0
        for idx, sym in enumerate(symbols):
            output_file = self.output_dir / f"{page_name}_symbol_{idx+1:03d}.png"
            sym['image'].save(output_file, 'PNG')
            saved += 1
        
        print(f"   ✅ Saved {saved} symbols to {self.output_dir}")
        return {'page': page_name, 'count': saved}
    
    def run(self):
        """Process all pages"""
        # Find all page images
        image_files = sorted(self.input_dir.glob("page_*.png"))
        
        if not image_files:
            print(f"❌ No page_*.png files found in {self.input_dir}")
            return
        
        print(f"🔍 Found {len(image_files)} pages to process")
        print("=" * 60)
        
        results = []
        for img_file in image_files:
            result = self.process_single_page(img_file)
            results.append(result)
        
        # Summary
        total_symbols = sum(r['count'] for r in results)
        
        print(f"\n{'='*60}")
        print("📊 EXTRACTION SUMMARY")
        print(f"{'='*60}")
        for r in results:
            print(f"   {r['page']}: {r['count']} symbols")
        print(f"\n   TOTAL: {total_symbols} symbols from {len(results)} pages")
        print(f"   Output: {self.output_dir}")

# ============================================
# SPECIAL HANDLER FOR PIPING SYMBOLS (Pages 12, 13)
# ============================================

class PipingSymbolHandler:
    """
    Specialized extractor for piping symbols that are horizontal lines with text
    """
    
    @staticmethod
    def extract_line_symbols(image_path: Path, output_dir: Path):
        """
        Extract horizontal line symbols common in piping diagrams
        """
        img = Image.open(image_path)
        width, height = img.size
        
        # Take left 60% (piping lines are long)
        left = img.crop((0, 0, int(width*0.6), height))
        img_array = np.array(left)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Invert
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Find horizontal lines using Hough transform or projection
        horizontal_proj = np.sum(binary, axis=1)
        
        # Find peaks (horizontal lines)
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(horizontal_proj, 
                                       height=100,  # Min line length
                                       distance=30)  # Min separation
        
        symbols = []
        for i, y in enumerate(peaks):
            # Extract region around line
            y_start = max(0, y - 25)
            y_end = min(height, y + 25)
            
            # Find horizontal extent
            line_slice = binary[y_start:y_end, :]
            x_proj = np.sum(line_slice, axis=0)
            x_nonzero = np.where(x_proj > 0)[0]
            
            if len(x_nonzero) > 0:
                x_start = max(0, x_nonzero[0] - 10)
                x_end = min(int(width*0.6), x_nonzero[-1] + 10)
                
                # Extract
                symbol_img = img_array[y_start:y_end, x_start:x_end]
                
                # Make transparent
                gray_sym = cv2.cvtColor(symbol_img, cv2.COLOR_RGB2GRAY) if len(symbol_img.shape)==3 else symbol_img
                _, alpha = cv2.threshold(gray_sym, 240, 255, cv2.THRESH_BINARY_INV)
                
                if len(symbol_img.shape) == 3:
                    r, g, b = cv2.split(cv2.cvtColor(symbol_img, cv2.COLOR_RGB2BGR))
                    rgba = cv2.merge([r, g, b, alpha])
                else:
                    rgba = cv2.cvtColor(symbol_img, cv2.COLOR_GRAY2RGBA)
                    rgba[:, :, 3] = alpha
                
                pil_img = Image.fromarray(rgba)
                symbols.append(pil_img)
        
        # Save flat structure inside output_dir
        page_name = image_path.stem
        for idx, sym in enumerate(symbols):
            sym.save(output_dir / f"{page_name}_line_symbol_{idx+1:03d}.png")
        
        return len(symbols)

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    # Windows paths - update these
    INPUT_DIR = r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project\data\temp_pages"
    OUTPUT_DIR = r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project\data\icons"
    
    # Empty icons directory first to prevent duplicate renames / ghosts
    out_path = Path(OUTPUT_DIR)
    if out_path.exists():
        for f in out_path.glob("*.png"):
            f.unlink()
    
    # Run universal extractor
    extractor = UniversalSymbolExtractor(INPUT_DIR, OUTPUT_DIR)
    extractor.run()
    
    # Special handling for page 12, 13 if needed
    print(f"\n{'='*60}")
    print("🔧 Running additional piping symbol detection...")
    
    for page in ['page_12.png', 'page_13.png']:
        page_path = Path(INPUT_DIR) / page
        if page_path.exists():
            try:
                count = PipingSymbolHandler.extract_line_symbols(
                    page_path, 
                    Path(OUTPUT_DIR)
                )
                print(f"   {page}: {count} line symbols extracted")
            except Exception as e:
                print(f"   {page}: Error - {e}")
