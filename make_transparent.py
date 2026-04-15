from PIL import Image
from pathlib import Path

ICONS_DIR = Path(r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION\HVAC_Project\data\icons")

def make_transparent(img_path):
    img = Image.open(img_path).convert("RGBA")
    data = img.getdata()
    
    new_data = []
    # Loop over pixels: if it's very bright (near white), make it transparent
    for item in data:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0)) # Transparent white
        else:
            new_data.append(item) # Keep black/gray ink
            
    img.putdata(new_data)
    img.save(img_path, "PNG")
    print(f"Processed: {img_path.name}")

if __name__ == "__main__":
    count = 0
    # Process all renamed specific files
    target_files = [
        "CON_REC.png", "CON_WH.png", "FCU_REC.png", "FCU_CAB.png",
        "TWU.png", "PTAC_WIN.png", "HP.png", "HP2.png", "AC_CUR.png",
        "UH_HOR.png", "UH_VER.png", "RCP_22.png", "RCP_24.png"
    ]
    
    for f in target_files:
        path = ICONS_DIR / f
        if path.exists():
            make_transparent(path)
            count += 1
            
    print(f"\nSuccessfully made {count} symbols transparent!")
