# ============================================================================
# day2_pdf_to_image.py — Day 2: PDF to High-Resolution Image Pipeline
# ============================================================================
#
# 🎯 OBJECTIVE: (Kya karenge?)
#   PDF file ko ek HIGH-QUALITY image mein convert karna.
#   AI ko agar low-quality image dein toh woh choti text nahi parh payega.
#   Isliye hum "Zoom Matrix" use karte hain taake output 4x sharp ho.
#
# 📝 HOW TO RUN:
#   Terminal mein jao, HVAC_Project folder mein, aur type karo:
#       python day2_pdf_to_image.py
#
# 🔗 DEPENDS ON:
#   - config.py (settings file)
#   - Day 1 ka setup complete hona chahiye
#   - data/input_pdf/drawing.pdf exist karni chahiye
#
# ============================================================================

import fitz          # PyMuPDF — PDF read karne ka sabse powerful library
import cv2           # OpenCV  — Image processing ka industry standard
import numpy as np   # NumPy   — Arrays/Matrices ke liye (image = matrix)
import os            # OS      — File paths aur folder operations
import logging       # Logging — Har step ka record rakhna (debugging ke liye)
import time          # Time    — Kitna time laga yeh measure karne ke liye

from config import CONFIG


# ============================================================================
# LOGGING SETUP
# ============================================================================
# Logging ka matlab hai ke program apne actions ka "diary" likhta hai.
# Agar kuch galat ho toh logs/system.log mein dekh sakte ho kya hua tha.
#
# Levels:
#   INFO    = Normal information (sab theek hai)
#   WARNING = Kuch suspicious hai but program chal raha hai
#   ERROR   = Kuch galat ho gaya
#   DEBUG   = Bahut detailed info (developers ke liye)

# Logs folder banao agar nahi hai
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)

logging.basicConfig(
    filename=CONFIG["LOG_FILE"],      # Log file ka path
    level=logging.INFO,               # Minimum level: INFO aur usse upar
    format='%(asctime)s - %(levelname)s - %(message)s',  # Format: time - level - message
    datefmt='%Y-%m-%d %H:%M:%S'       # Date format: 2026-04-01 21:30:00
)

# Console pe bhi logs dikhana hai (sirf file mein nahi)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger().addHandler(console_handler)


# ============================================================================
# CLASS: PDFConverter
# ============================================================================
# Class ka matlab hai ek "blueprint" — jaise building ka naksha.
# Is class mein PDF se related saare functions hain.
# Class use karne ka faida: organized code, reusable, easy to test.

class PDFConverter:
    """
    PDF file ko high-resolution image (NumPy array) mein convert karta hai.
    
    ENGINEERING CONTEXT:
        EPC Shop Drawings (jaise RAPCO ke) mein text bahut choti hoti hai.
        Normal 72 DPI pe "200x200 L/A" jaisi text pixels mein gum ho jati hai.
        Hum 4x zoom use karte hain = 288 DPI, jisse AI clearly parh sake.
    
    USAGE:
        converter = PDFConverter()              # Object banao
        image = converter.convert("path.pdf")   # PDF ko image mein badlo
        converter.save_image(image, "out.png")  # Image file save karo
    """
    
    def __init__(self):
        """
        Constructor — Jab PDFConverter() likhte hain toh yeh automatically chalta hai.
        Settings config.py se load hoti hain.
        """
        self.zoom = CONFIG["ZOOM"]           # Zoom level (4.0 = 4x enlarge)
        self.save_format = CONFIG.get("SAVE_FORMAT", "png")  # Output format
        
        logging.info(f"PDFConverter initialized with ZOOM={self.zoom}")
    
    
    def convert(self, pdf_path, page_number=0):
        """
        PDF ki ek page ko high-resolution NumPy image array mein convert karta hai.
        
        STEP-BY-STEP:
            1. PDF file open karo
            2. Specified page load karo
            3. Zoom Matrix apply karo (image enlarge karne ke liye)
            4. Pixmap (raw pixels) generate karo
            5. Pixmap ko NumPy array mein convert karo
            6. RGB → BGR convert karo (OpenCV ka format BGR hai)
        
        Parameters:
            pdf_path    : PDF file ka full path (string)
            page_number : Kaunsi page convert karni hai (0 = pehli page)
        
        Returns:
            NumPy array — Image as a matrix of pixels
            Shape: (height, width, 3) — 3 = BGR color channels
        
        Raises:
            FileNotFoundError : Agar PDF file exist nahi karti
            Exception         : Agar PDF corrupt hai ya read nahi ho paa rahi
        """
        
        # ---------------------------------------------------------------
        # CHECK 1: File exist karti hai?
        # ---------------------------------------------------------------
        if not os.path.exists(pdf_path):
            error_msg = f"PDF file not found: {pdf_path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # ---------------------------------------------------------------
        # CHECK 2: File actually PDF hai? (.pdf extension check)
        # ---------------------------------------------------------------
        if not pdf_path.lower().endswith('.pdf'):
            logging.warning(f"File does not have .pdf extension: {pdf_path}")
        
        # ---------------------------------------------------------------
        # STEP 1: PDF Open Karo
        # ---------------------------------------------------------------
        # fitz.open() = PyMuPDF ka function jo PDF ko memory mein load karta hai
        # "doc" = document object, iske through pages access karte hain
        
        start_time = time.time()    # Timer shuru (performance measure ke liye)
        logging.info(f"Opening PDF: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logging.error(f"Cannot open PDF: {e}")
            raise RuntimeError(f"Failed to open PDF file: {e}")
        
        # ---------------------------------------------------------------
        # STEP 2: Page Load Karo
        # ---------------------------------------------------------------
        # doc.page_count = total pages in PDF
        # doc.load_page(0) = pehli page load karo (0-indexed)
        
        total_pages = doc.page_count
        logging.info(f"PDF has {total_pages} page(s). Loading page {page_number + 1}...")
        
        if page_number < 0 or page_number >= total_pages:
            doc.close()
            raise ValueError(
                f"Page {page_number} does not exist. "
                f"PDF has {total_pages} pages (0 to {total_pages - 1})."
            )
        
        page = doc.load_page(page_number)
        
        # Original page size (in points, 72 points = 1 inch)
        original_rect = page.rect
        logging.info(
            f"Original page size: {original_rect.width:.0f} x {original_rect.height:.0f} pts "
            f"({original_rect.width/72:.1f}\" x {original_rect.height/72:.1f}\")"
        )
        
        # ---------------------------------------------------------------
        # STEP 3: Zoom Matrix Banao
        # ---------------------------------------------------------------
        # fitz.Matrix(zoom_x, zoom_y) = ek transformation matrix
        #
        # SIMPLE EXPLANATION:
        #   Agar page 1000x800 pts hai aur zoom = 4.0, toh output image:
        #   Width  = 1000 × 4 = 4000 pixels
        #   Height = 800 × 4  = 3200 pixels
        #
        # WHY ZOOM?
        #   Normal rendering = 72 DPI (dots per inch)
        #   zoom=4 → 72 × 4 = 288 DPI — engineering drawings ke liye BEST
        #   zoom=2 → 72 × 2 = 144 DPI — okay for simple drawings
        
        mat = fitz.Matrix(self.zoom, self.zoom)
        effective_dpi = 72 * self.zoom
        logging.info(f"Zoom Matrix: {self.zoom}x → Effective DPI: {effective_dpi:.0f}")
        
        # ---------------------------------------------------------------
        # STEP 4: Pixmap Generate Karo (Raw Pixel Data)
        # ---------------------------------------------------------------
        # page.get_pixmap() = page ko pixels mein render karta hai
        # matrix=mat yeh batata hai ke kitna zoom karna hai
        #
        # Pixmap = Pixel Map = har pixel ka color data
        # pix.samples = raw byte data (R, G, B values)
        # pix.w = width in pixels
        # pix.h = height in pixels
        # pix.n = number of color channels (3 = RGB, 4 = RGBA)
        
        logging.info("Rendering page to high-resolution pixmap...")
        pix = page.get_pixmap(matrix=mat)
        
        logging.info(
            f"Pixmap generated: {pix.w} x {pix.h} pixels, "
            f"{pix.n} channels, "
            f"~{(pix.w * pix.h * pix.n) / (1024*1024):.1f} MB in memory"
        )
        
        # ---------------------------------------------------------------
        # STEP 5: Pixmap → NumPy Array
        # ---------------------------------------------------------------
        # NumPy array = matrix (rows × columns × channels)
        # Example: 4000×3200 image with 3 colors = 4000 × 3200 × 3 = 38.4M values
        #
        # np.frombuffer() = raw bytes ko NumPy array mein convert karta hai
        # dtype=np.uint8  = har value 0-255 ke beech hai (pixel brightness)
        # .reshape()      = flat array ko 3D matrix shape mein badalta hai
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        
        # ---------------------------------------------------------------
        # STEP 6: Color Space Convert — RGB → BGR
        # ---------------------------------------------------------------
        # PyMuPDF RGB format mein deta hai (Red, Green, Blue)
        # OpenCV BGR format use karta hai (Blue, Green, Red)
        # Agar convert nahi karein toh colors ulte dikhenge!
        #
        # RGBA (4 channels) = transparency wali images ke liye
        
        if pix.n == 4:
            # RGBA → BGR (transparency channel hata do)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            # RGB → BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        # pix.n == 1 means grayscale, no conversion needed
        
        # ---------------------------------------------------------------
        # CLEANUP & REPORTING
        # ---------------------------------------------------------------
        doc.close()   # PDF file close karo (memory free karo)
        
        elapsed = time.time() - start_time   # Kitna time laga
        
        logging.info(
            f"✅ PDF → Image conversion complete! "
            f"Size: {img.shape[1]}x{img.shape[0]} px | "
            f"Time: {elapsed:.2f}s"
        )
        
        return img
    
    
    def save_image(self, image, output_path):
        """
        NumPy image array ko file mein save karta hai.
        
        Parameters:
            image       : NumPy array (cv2 format BGR)
            output_path : Kahan save karna hai (e.g., "data/output/drawing.png")
        
        Returns:
            bool — True agar save ho gayi, False agar nahi
        """
        
        try:
            # Output folder banao agar nahi hai
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # cv2.imwrite() = image ko file mein save karta hai
            # Format automatically extension se detect hota hai (.png, .jpg)
            success = cv2.imwrite(output_path, image)
            
            if success:
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logging.info(f"Image saved: {output_path} ({file_size_mb:.2f} MB)")
                return True
            else:
                logging.error(f"cv2.imwrite failed for: {output_path}")
                return False
                
        except Exception as e:
            logging.error(f"Error saving image: {e}")
            return False
    
    
    def get_image_info(self, image):
        """
        Image ki detailed information return karta hai.
        Debugging ke liye useful.
        
        Parameters:
            image : NumPy array
        
        Returns:
            dict — Image properties
        """
        
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1
        
        info = {
            "width_px": width,
            "height_px": height,
            "channels": channels,
            "dtype": str(image.dtype),
            "memory_mb": round(image.nbytes / (1024 * 1024), 2),
            "aspect_ratio": round(width / height, 3) if height > 0 else 0,
        }
        
        return info


# ============================================================================
# MAIN EXECUTION — Jab "python day2_pdf_to_image.py" run karo
# ============================================================================

if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 2: PDF TO HIGH-RESOLUTION IMAGE PIPELINE")
    print("=" * 60)
    
    # --- Step 1: PDFConverter object banao ---
    print("\n📋 Step 1: Initializing PDF Converter...")
    converter = PDFConverter()
    
    # --- Step 2: PDF ka path config se lo ---
    pdf_path = CONFIG["INPUT_PATH"]
    print(f"  📍 PDF Path: {pdf_path}")
    
    # Check karo ke PDF exist karti hai
    if not os.path.exists(pdf_path):
        print(f"\n  ⚠️  PDF file not found!")
        print(f"  👉 Place your PDF at: {pdf_path}")
        
        # Koi aur PDF project root mein hai toh use kar lo
        base_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(base_dir)
        all_pdfs = []
        for root, dirs, files in os.walk(parent_dir):
            for f in files:
                if f.lower().endswith('.pdf'):
                    all_pdfs.append(os.path.join(root, f))
        
        if all_pdfs:
            print(f"\n  💡 Found these PDFs nearby:")
            for i, p in enumerate(all_pdfs[:5]):
                print(f"     [{i+1}] {p}")
            print(f"\n  👉 Copy one of these to: {os.path.dirname(pdf_path)}")
            print(f"     and rename it to 'drawing.pdf'")
    else:
        # --- Step 3: Convert! ---
        print(f"\n📋 Step 2: Converting PDF to image...")
        image = converter.convert(pdf_path)
        
        # --- Step 4: Image info dikhao ---
        info = converter.get_image_info(image)
        print(f"\n  📊 Output Image Details:")
        print(f"  {'Width':15s}: {info['width_px']} pixels")
        print(f"  {'Height':15s}: {info['height_px']} pixels")
        print(f"  {'Channels':15s}: {info['channels']} (BGR color)")
        print(f"  {'Memory':15s}: {info['memory_mb']} MB")
        print(f"  {'Aspect Ratio':15s}: {info['aspect_ratio']}")
        
        # --- Step 5: Save the image ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(base_dir, "data", "drawing_high_res.png")
        
        print(f"\n📋 Step 3: Saving high-resolution image...")
        saved = converter.save_image(image, output_path)
        
        if saved:
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✅ Saved to: {output_path}")
            print(f"  📦 File size: {size_mb:.2f} MB")
        
        # --- SUMMARY ---
        print("\n" + "=" * 60)
        print("  📋 DAY 2 SUMMARY")
        print("=" * 60)
        print(f"  PDF Input    : {os.path.basename(pdf_path)}")
        print(f"  Zoom Level   : {CONFIG['ZOOM']}x ({72 * CONFIG['ZOOM']:.0f} DPI)")
        print(f"  Output Size  : {info['width_px']} x {info['height_px']} pixels")
        print(f"  Image Saved  : ✅ {os.path.basename(output_path)}")
        print(f"\n  🎉 DAY 2 COMPLETE! Ready for Day 3.")
        print("=" * 60)
