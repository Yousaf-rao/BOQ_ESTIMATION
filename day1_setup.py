# ============================================================================
# day1_setup.py — Day 1: Project Setup & "Hello World" PDF Test
# ============================================================================
#
# 🎯 OBJECTIVE: (Kya karenge?)
#   1. Project ke saare folders automatically create karna
#   2. Check karna ke saari required libraries install hain ya nahi
#   3. PDF file ko open karke uski basic info print karna
#   4. Agar sab kuch sahi chale, toh Day 1 COMPLETE! ✅
#
# 📝 HOW TO RUN:
#   Terminal mein jao, HVAC_Project folder mein, aur type karo:
#       python day1_setup.py
#
# ⚠️ BEFORE RUNNING:
#   Make sure aapne install kiya hai:
#       pip install PyMuPDF opencv-python pillow numpy
#
# ============================================================================

import os       # OS = Operating System: folders banana, paths check karna
import sys      # SYS = System: Python version check karna, program exit karna


# ============================================================================
# STEP 1: Folder Structure Create Karna
# ============================================================================
# Engineering projects mein organized folder structure BAHUT zaroori hai.
# Yeh function automatically saare folders bana deta hai.

def create_folder_structure():
    """
    Project ke liye zaroori folders banata hai agar exist nahi karte.
    
    Folder Structure:
        HVAC_Project/
        ├── data/
        │   ├── input_pdf/    ← PDF yahan rakhni hai
        │   ├── output_tiles/ ← AI ke liye tiles yahan banenge
        │   └── legends/      ← Legend/Title block yahan save hoga
        └── logs/             ← Error aur status logs yahan aayegi
    """
    
    print("\n📁 Step 1: Creating Folder Structure...")
    print("-" * 50)
    
    # BASE_DIR = Yeh file jis folder mein hai (HVAC_Project/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Saare folders jo banana hain unki list
    folders = [
        os.path.join(base_dir, "data", "input_pdf"),     # PDF files ke liye
        os.path.join(base_dir, "data", "output_tiles"),   # Tiles ke liye
        os.path.join(base_dir, "data", "legends"),        # Legend images ke liye
        os.path.join(base_dir, "logs"),                   # Log files ke liye
    ]
    
    for folder in folders:
        # os.makedirs() = folders banata hai
        # exist_ok=True = agar pehle se hai toh error NAHI dega
        os.makedirs(folder, exist_ok=True)
        
        # Relative path dikhao (clean output ke liye)
        relative = os.path.relpath(folder, base_dir)
        print(f"  ✅ Created: {relative}/")
    
    print(f"\n  📍 Base Directory: {base_dir}")
    return base_dir


# ============================================================================
# STEP 2: Libraries Check Karna
# ============================================================================
# Yeh function check karta hai ke saari zaroori libraries install hain.
# Agar koi missing hai toh bata dega kaise install karni hai.

def check_dependencies():
    """
    Check karta hai ke zaroori Python libraries install hain ya nahi.
    
    Required Libraries:
        - fitz (PyMuPDF): PDF files read karne ke liye
        - cv2 (OpenCV): Image processing ke liye
        - numpy: Mathematical operations ke liye
        - PIL (Pillow): Extra image handling ke liye
    """
    
    print("\n🔍 Step 2: Checking Required Libraries...")
    print("-" * 50)
    
    # Har library ka naam aur uska kaam
    # Format: (import_name, pip_install_name, description)
    required_libs = [
        ("fitz",    "PyMuPDF",        "PDF files ko read aur render karna"),
        ("cv2",     "opencv-python",  "Image processing (crop, resize, etc.)"),
        ("numpy",   "numpy",          "Mathematical arrays aur calculations"),
        ("PIL",     "Pillow",         "Image format handling (PNG, JPG, etc.)"),
    ]
    
    all_ok = True       # Track karta hai ke sab install hain ya nahi
    missing = []        # Missing libraries ki list
    
    for lib_import, lib_pip, lib_desc in required_libs:
        try:
            # __import__() dynamically kisi bhi library ko import karta hai
            module = __import__(lib_import)
            
            # Version nikalo (har library ka different attribute hota hai)
            version = getattr(module, '__version__', 
                     getattr(module, 'version', 'unknown'))
            
            print(f"  ✅ {lib_pip:20s} v{version:10s} — {lib_desc}")
            
        except ImportError:
            # Agar library nahi mili toh error message
            print(f"  ❌ {lib_pip:20s} {'MISSING':10s} — {lib_desc}")
            missing.append(lib_pip)
            all_ok = False
    
    # Summary
    if missing:
        print(f"\n  ⚠️  Missing libraries found! Install them with:")
        print(f"      pip install {' '.join(missing)}")
        return False
    else:
        print(f"\n  🎉 All libraries are installed correctly!")
        return True


# ============================================================================
# STEP 3: PDF "Hello World" Test
# ============================================================================
# Yeh step sabse important hai — verify karta hai ke PDF file accessible hai
# aur PyMuPDF usko properly read kar pa raha hai.

def test_pdf_reading(pdf_path=None):
    """
    PDF file ko open karke uski basic information print karta hai.
    
    Yeh function check karta hai:
        1. Kya file exist karti hai?
        2. Kya PyMuPDF usko open kar sakta hai?
        3. Pages kitne hain?
        4. Har page ka size kya hai?
    
    Parameters:
        pdf_path: PDF file ka full path. Agar None hai toh config se lega.
    """
    
    print("\n📄 Step 3: PDF 'Hello World' Test...")
    print("-" * 50)
    
    # Agar path nahi diya toh config.py se le lo
    if pdf_path is None:
        try:
            from config import CONFIG
            pdf_path = CONFIG["INPUT_PATH"]
        except ImportError:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            pdf_path = os.path.join(base_dir, "data", "input_pdf", "drawing.pdf")
    
    # --- Check 1: File Exist Karti Hai? ---
    print(f"  📍 Looking for PDF at: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"\n  ⚠️  PDF file nahi mili!")
        print(f"  👉 Apni PDF file yahan rakhein:")
        print(f"     {pdf_path}")
        print(f"  👉 Ya phir kisi bhi test PDF ka naam 'drawing.pdf' rakh ke")
        print(f"     data/input_pdf/ folder mein daalo.")
        
        # Check karo ke koi aur PDF hai toh wo bata do
        input_dir = os.path.dirname(pdf_path)
        if os.path.exists(input_dir):
            pdfs = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
            if pdfs:
                print(f"\n  💡 Yeh PDFs mili hain input folder mein:")
                for p in pdfs:
                    print(f"     - {p}")
        return False
    
    # --- Check 2: PDF Open Karo ---
    try:
        import fitz   # PyMuPDF
        
        doc = fitz.open(pdf_path)
        
        # --- Basic Information ---
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        print(f"\n  📊 PDF Information:")
        print(f"  {'File Name':20s}: {os.path.basename(pdf_path)}")
        print(f"  {'File Size':20s}: {file_size_mb:.2f} MB")
        print(f"  {'Total Pages':20s}: {doc.page_count}")
        print(f"  {'PDF Format':20s}: {doc.metadata.get('format', 'N/A')}")
        print(f"  {'Creator':20s}: {doc.metadata.get('creator', 'N/A')}")
        
        # --- Har Page Ki Info ---
        print(f"\n  📐 Page Details:")
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            rect = page.rect   # Page ka rectangle (dimensions)
            
            # Points ko inches mein convert karo (72 points = 1 inch)
            width_inches = rect.width / 72
            height_inches = rect.height / 72
            
            print(f"     Page {page_num + 1}: {rect.width:.0f} x {rect.height:.0f} pts "
                  f"({width_inches:.1f}\" x {height_inches:.1f}\")")
        
        doc.close()
        
        print(f"\n  🎉 PDF opened and read successfully!")
        return True
        
    except Exception as e:
        print(f"\n  ❌ Error reading PDF: {e}")
        print(f"  💡 Make sure the PDF is not corrupted or password-protected.")
        return False


# ============================================================================
# STEP 4: System Info (Bonus)
# ============================================================================
# Yeh debugging ke liye useful hai — system ki info dikhata hai

def show_system_info():
    """
    System ki basic information dikhata hai.
    Useful hai agar kisi aur computer pe code chalana ho.
    """
    
    print("\n💻 System Information:")
    print("-" * 50)
    print(f"  Python Version  : {sys.version.split()[0]}")
    print(f"  Platform        : {sys.platform}")
    print(f"  Working Dir     : {os.getcwd()}")
    print(f"  Script Location : {os.path.dirname(os.path.abspath(__file__))}")


# ============================================================================
# MAIN EXECUTION — Jab "python day1_setup.py" run karo
# ============================================================================

if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 1: PROJECT SETUP & HELLO WORLD PDF TEST")
    print("=" * 60)
    
    # Step 1: Folders banao
    base_dir = create_folder_structure()
    
    # Step 2: Libraries check karo
    libs_ok = check_dependencies()
    
    # Step 3: PDF test karo
    pdf_ok = test_pdf_reading()
    
    # Step 4: System info dikhao
    show_system_info()
    
    # ========================
    # FINAL SUMMARY
    # ========================
    print("\n" + "=" * 60)
    print("  📋 DAY 1 SUMMARY")
    print("=" * 60)
    
    print(f"  Folders Created  : ✅ Done")
    print(f"  Libraries Check  : {'✅ All Installed' if libs_ok else '❌ Some Missing'}")
    print(f"  PDF Test         : {'✅ Passed' if pdf_ok else '⚠️  PDF not found (add it later)'}")
    
    if libs_ok:
        print(f"\n  🎉 DAY 1 COMPLETE! Ready for Day 2.")
    else:
        print(f"\n  ⚠️  Install missing libraries first, then run again.")
    
    print("=" * 60)
