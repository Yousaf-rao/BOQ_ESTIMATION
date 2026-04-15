# ============================================================================
# day3_opencv_basics.py — Day 3: Mastering Basic OpenCV (Image Manipulation)
# ============================================================================
#
# 🎯 OBJECTIVE:
#   Learn the basic skills of the OpenCV library:
#   1. Load an image (cv2.imread)
#   2. Convert Color → Grayscale
#   3. Crop (slice) an image — cut any section and save it separately
#   4. Resize an image
#   5. View basic image information
#
#   These skills will be used in Day 4 (Legend Extraction) and Day 5-6 (Tiling).
#
# 📝 HOW TO RUN:
#       python day3_opencv_basics.py
#
# 🔗 DEPENDS ON:
#   - Day 2 must be complete (drawing_high_res.png must exist)
#   - If Day 2 output is missing, this script will generate a demo image
#
# ============================================================================

import cv2           # OpenCV  — Image processing library
import numpy as np   # NumPy   — Image = NumPy array (matrix of numbers)
import os            # OS      — File/folder operations
import logging       # Logging — For tracking progress

from config import CONFIG

# Logging setup
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ============================================================================
# CONCEPT: What is an Image?
# ============================================================================
#
# For a computer, an image = A MATRIX OF NUMBERS (grid of numbers)
#
# Example (3x3 grayscale image):
#   [[ 0,   128, 255],
#    [ 64,  192, 32 ],
#    [ 200, 100, 50 ]]
#
#   0   = Pure Black
#   255 = Pure White
#   128 = Gray (in between)
#
# Color Image = 3D Matrix (height × width × 3)
#   3 channels: Blue, Green, Red (OpenCV ka order = BGR)
#
# Example pixel: [255, 0, 0] = Pure Blue
#                [0, 255, 0] = Pure Green
#                [0, 0, 255] = Pure Red
#
# ============================================================================


class OpenCVBasics:
    """
    Class to learn basic image processing operations using OpenCV.
    
    This class teaches step-by-step:
        1. How to load an image
        2. How to convert an image to grayscale
        3. How to crop a specific part of an image
        4. How to resize an image
    
    Every function contains comments explaining what is happening.
    """
    
    def __init__(self):
        """Constructor — Set up the output folder"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.practice_dir = os.path.join(self.base_dir, "data", "practice")
        os.makedirs(self.practice_dir, exist_ok=True)
    
    
    def load_image(self, image_path):
        """
        SKILL 1: Loading an Image File
        
        The cv2.imread() function reads the image file and returns a NumPy array.
        
        Parameters:
            image_path : Path of the image file (PNG, JPG, BMP, etc.)
        
        Returns:
            NumPy array (BGR format) or None if load fails.
        
        IMPORTANT FLAGS:
            cv2.IMREAD_COLOR      = Load in color (default)
            cv2.IMREAD_GRAYSCALE  = Directly load in grayscale
            cv2.IMREAD_UNCHANGED  = Retain the transparency channel (RGBA)
        """
        
        print(f"\n  📷 Loading image: {os.path.basename(image_path)}")
        
        # --- Check: File exist karti hai? ---
        if not os.path.exists(image_path):
            print(f"  ❌ File not found: {image_path}")
            return None
        
        # --- cv2.imread() — Image ko padho ---
        # Yeh function image ko BGR format mein load karta hai
        # BGR = Blue, Green, Red (OpenCV ka default color order)
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"  ❌ OpenCV could not read this file. Corrupted?")
            return None
        
        # --- Image ki info print karo ---
        height, width, channels = img.shape
        print(f"  ✅ Image loaded successfully!")
        print(f"     Dimensions : {width} x {height} pixels")
        print(f"     Channels   : {channels} (BGR)")
        print(f"     Data Type  : {img.dtype}")
        print(f"     Memory     : {img.nbytes / (1024*1024):.2f} MB")
        
        logging.info(f"Image loaded: {image_path} — {width}x{height}")
        return img
    
    
    def convert_to_grayscale(self, img, save_path=None):
        """
        SKILL 2: Converting Color Image to Grayscale
        
        WHY GRAYSCALE?
            - Grayscale has only 1 channel (0-255, black to white)
            - Color has 3 channels (B, G, R)
            - Grayscale benefits:
                1. File size is reduced by 3x
                2. Processing is 3x faster
                3. Symbol detection becomes easier (only shapes matter)
            - Color is usually not important in engineering drawings.
        
        Parameters:
            img       : Color image (NumPy array, BGR)
            save_path : If provided, the grayscale image will be saved here.
        
        Returns:
            Grayscale image (NumPy array, single channel)
        """
        
        print(f"\n  🎨 Converting to Grayscale...")
        
        # cv2.cvtColor() = Color space conversion
        # COLOR_BGR2GRAY = BGR (3 channels) → Gray (1 channel)
        #
        # Formula internally:
        #   Gray = 0.299 × Red + 0.587 × Green + 0.114 × Blue
        #   (Human eyes green ko zyada bright dekhte hain, isliye green ka weight zyada hai)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        print(f"  ✅ Converted! Shape changed: {img.shape} → {gray.shape}")
        print(f"     Before: {img.nbytes / (1024*1024):.2f} MB")
        print(f"     After : {gray.nbytes / (1024*1024):.2f} MB")
        print(f"     Saved : {(1 - gray.nbytes/img.nbytes) * 100:.0f}% memory reduction")
        
        # Save agar path diya hai
        if save_path:
            cv2.imwrite(save_path, gray)
            print(f"  💾 Saved to: {os.path.basename(save_path)}")
        
        logging.info(f"Grayscale conversion: {img.shape} → {gray.shape}")
        return gray
    
    
    def crop_region(self, img, x_start, y_start, x_end, y_end, save_path=None):
        """
        SKILL 3: Crop (Slice) Any Section of an Image
        
        CONCEPT — NumPy Slicing:
            An image is a matrix: img[row, column] = img[y, x]
            
            ⚠️ IMPORTANT: In OpenCV, the order of coordinates is:
                img[y_start : y_end, x_start : x_end]
                     ↑ rows (vertical)   ↑ columns (horizontal)
            
            Meaning: y (up-down) goes FIRST, THEN x (left-right).
        
        VISUAL EXPLANATION:
            Original Image (1000 x 800):
            ┌──────────────────────────────┐
            │                              │  ← y=0 (top)
            │       ┌──────────┐           │
            │       │ CROPPED  │           │  ← y_start
            │       │  REGION  │           │
            │       └──────────┘           │  ← y_end
            │       ↑          ↑           │
            │    x_start    x_end          │
            │                              │  ← y=800 (bottom)
            └──────────────────────────────┘
        
        Parameters:
            img     : Source image (NumPy array)
            x_start : Left edge (column start)
            y_start : Top edge (row start)
            x_end   : Right edge (column end)
            y_end   : Bottom edge (row end)
            save_path : Optional save location
        
        Returns:
            Cropped image (NumPy array)
        """
        
        print(f"\n  ✂️  Cropping region: ({x_start},{y_start}) to ({x_end},{y_end})")
        
        # Image dimensions lo
        h, w = img.shape[:2]
        
        # --- Safety Checks ---
        # Coordinates image se bahar nahi hone chahiye
        x_start = max(0, x_start)           # Minimum 0
        y_start = max(0, y_start)           # Minimum 0
        x_end   = min(w, x_end)             # Maximum = image width
        y_end   = min(h, y_end)             # Maximum = image height
        
        if x_end <= x_start or y_end <= y_start:
            print(f"  ❌ Invalid crop region! Check coordinates.")
            return None
        
        # --- THE ACTUAL CROP — NumPy Slicing ---
        # img[y_start:y_end, x_start:x_end]
        # Yeh line image ka ek rectangular piece kaat ke deta hai
        # NO COPY hoti — yeh original image ka "view" hai (memory efficient)
        
        cropped = img[y_start:y_end, x_start:x_end].copy()
        # .copy() use karte hain taake yeh independent ho (original se linked na rahe)
        
        crop_h, crop_w = cropped.shape[:2]
        print(f"  ✅ Cropped! New size: {crop_w} x {crop_h} pixels")
        
        # Save agar path diya hai
        if save_path:
            cv2.imwrite(save_path, cropped)
            print(f"  💾 Saved to: {os.path.basename(save_path)}")
        
        logging.info(f"Cropped region ({x_start},{y_start})-({x_end},{y_end}) → {crop_w}x{crop_h}")
        return cropped
    
    
    def resize_image(self, img, new_width=None, new_height=None, scale=None, save_path=None):
        """
        SKILL 4: Image Ka Size Change Karna (Resize)
        
        3 METHODS:
            1. new_width + new_height = exact size set karo
            2. scale = percentage se resize karo (0.5 = half, 2.0 = double)
            3. sirf width ya height do = aspect ratio maintain hoga
        
        INTERPOLATION (Kaise pixels add/remove hote hain):
            cv2.INTER_AREA    = Shrinking ke liye BEST (smooth result)
            cv2.INTER_LINEAR  = Default (fast, good quality)
            cv2.INTER_CUBIC   = Enlarging ke liye BEST (sharp result)
        
        Parameters:
            img        : Source image
            new_width  : Target width (pixels)
            new_height : Target height (pixels)
            scale      : Scale factor (0.5 = half, 2.0 = double)
            save_path  : Optional save location
        
        Returns:
            Resized image (NumPy array)
        """
        
        h, w = img.shape[:2]
        
        if scale is not None:
            # Scale se new dimensions calculate karo
            new_width = int(w * scale)
            new_height = int(h * scale)
        elif new_width is not None and new_height is None:
            # Sirf width di — height proportional calculate karo
            ratio = new_width / w
            new_height = int(h * ratio)
        elif new_height is not None and new_width is None:
            # Sirf height di — width proportional calculate karo
            ratio = new_height / h
            new_width = int(w * ratio)
        elif new_width is None and new_height is None:
            print("  ❌ Provide at least width, height, or scale!")
            return img
        
        print(f"\n  📐 Resizing: {w}x{h} → {new_width}x{new_height}")
        
        # Choose interpolation method based on whether we're shrinking or enlarging
        if new_width * new_height < w * h:
            interpolation = cv2.INTER_AREA     # Shrinking → INTER_AREA best hai
        else:
            interpolation = cv2.INTER_CUBIC    # Enlarging → INTER_CUBIC best hai
        
        # cv2.resize() = image ka size change karta hai
        resized = cv2.resize(img, (new_width, new_height), interpolation=interpolation)
        
        print(f"  ✅ Resized successfully!")
        
        if save_path:
            cv2.imwrite(save_path, resized)
            print(f"  💾 Saved to: {os.path.basename(save_path)}")
        
        return resized
    
    
    def create_demo_image(self):
        """
        Demo image banata hai agar Day 2 ka output available nahi hai.
        Testing ke liye useful.
        
        Returns:
            Demo image (NumPy array) aur uska save path
        """
        
        print(f"\n  🎨 Creating demo image for practice...")
        
        # 800x600 white image banao (3 channels = BGR)
        # np.ones() = saare values 1 — multiply by 255 = white
        demo = np.ones((600, 800, 3), dtype=np.uint8) * 255
        
        # Kuch shapes draw karo (simulate engineering drawing)
        # cv2.rectangle(image, start_point, end_point, color_BGR, thickness)
        cv2.rectangle(demo, (50, 50), (750, 550), (0, 0, 0), 2)           # Border
        cv2.rectangle(demo, (600, 50), (750, 550), (200, 200, 200), -1)   # Legend area (gray)
        
        # Lines draw karo (simulate ducts)
        cv2.line(demo, (100, 200), (550, 200), (0, 0, 0), 2)    # Horizontal duct
        cv2.line(demo, (300, 100), (300, 400), (0, 0, 0), 2)    # Vertical duct
        
        # Circles draw karo (simulate diffusers)
        cv2.circle(demo, (200, 300), 20, (0, 0, 255), -1)   # Red circle = supply
        cv2.circle(demo, (400, 300), 20, (255, 0, 0), -1)   # Blue circle = return
        
        # Text add karo
        cv2.putText(demo, "HVAC FLOOR PLAN", (150, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        cv2.putText(demo, "LEGEND", (620, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(demo, "200 L/s", (170, 340), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # Save
        demo_path = os.path.join(self.practice_dir, "demo_drawing.png")
        cv2.imwrite(demo_path, demo)
        print(f"  ✅ Demo image saved: {demo_path}")
        
        return demo, demo_path


# ============================================================================
# MAIN EXECUTION — Jab "python day3_opencv_basics.py" run karo
# ============================================================================

if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 3: MASTERING BASIC OPENCV")
    print("=" * 60)
    
    basics = OpenCVBasics()
    
    # =====================================================
    # EXERCISE 1: Image Load Karo
    # =====================================================
    print("\n" + "=" * 60)
    print("  📘 EXERCISE 1: Loading an Image")
    print("=" * 60)
    
    # Day 2 ka output try karo, warna demo image banao
    high_res_path = os.path.join(basics.base_dir, "data", "drawing_high_res.png")
    
    if os.path.exists(high_res_path):
        print("  💡 Using Day 2 output: drawing_high_res.png")
        img = basics.load_image(high_res_path)
    else:
        print("  💡 Day 2 output not found. Creating demo image...")
        img, demo_path = basics.create_demo_image()
        img = basics.load_image(demo_path)
    
    if img is None:
        print("  ❌ Could not load any image. Exiting.")
        exit(1)
    
    # =====================================================
    # EXERCISE 2: Grayscale Conversion
    # =====================================================
    print("\n" + "=" * 60)
    print("  📘 EXERCISE 2: Color → Grayscale Conversion")
    print("=" * 60)
    
    gray_path = os.path.join(basics.practice_dir, "grayscale_output.png")
    gray = basics.convert_to_grayscale(img, save_path=gray_path)
    
    # =====================================================
    # EXERCISE 3: Cropping (Slicing)
    # =====================================================
    print("\n" + "=" * 60)
    print("  📘 EXERCISE 3: Cropping a Region")
    print("=" * 60)
    
    h, w = img.shape[:2]
    
    # Center area crop karo (beech ka 40% hissa)
    center_x = w // 2
    center_y = h // 2
    crop_w = int(w * 0.2)    # 20% width
    crop_h = int(h * 0.2)    # 20% height
    
    center_crop_path = os.path.join(basics.practice_dir, "center_crop.png")
    center_crop = basics.crop_region(
        img,
        x_start=center_x - crop_w,
        y_start=center_y - crop_h,
        x_end=center_x + crop_w,
        y_end=center_y + crop_h,
        save_path=center_crop_path
    )
    
    # Top-left corner crop karo
    corner_path = os.path.join(basics.practice_dir, "top_left_corner.png")
    corner = basics.crop_region(
        img,
        x_start=0,
        y_start=0,
        x_end=int(w * 0.25),
        y_end=int(h * 0.25),
        save_path=corner_path
    )
    
    # =====================================================
    # EXERCISE 4: Resizing
    # =====================================================
    print("\n" + "=" * 60)
    print("  📘 EXERCISE 4: Resizing Image")
    print("=" * 60)
    
    # Half size
    half_path = os.path.join(basics.practice_dir, "resized_half.png")
    half = basics.resize_image(img, scale=0.5, save_path=half_path)
    
    # Fixed width (800px, height proportional)
    fixed_path = os.path.join(basics.practice_dir, "resized_800w.png")
    fixed = basics.resize_image(img, new_width=800, save_path=fixed_path)
    
    # =====================================================
    # FINAL SUMMARY
    # =====================================================
    print("\n" + "=" * 60)
    print("  📋 DAY 3 SUMMARY")
    print("=" * 60)
    print(f"  Exercise 1 — Load Image     : ✅ Done")
    print(f"  Exercise 2 — Grayscale      : ✅ Saved")
    print(f"  Exercise 3 — Cropping       : ✅ 2 crops saved")
    print(f"  Exercise 4 — Resizing       : ✅ 2 resized images saved")
    print(f"\n  📁 All practice outputs in: {basics.practice_dir}")
    print(f"\n  🎉 DAY 3 COMPLETE! Ready for Day 4.")
    print("=" * 60)
