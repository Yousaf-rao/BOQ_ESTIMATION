from PIL import Image
from pathlib import Path
import sys

def make_transparent(input_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    newData = []
    for item in datas:
        # Check if pixel is white or nearly white (e.g., > 240 for R, G, B)
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            newData.append((255, 255, 255, 0)) # Make it transparent
        else:
            newData.append(item)
    img.putdata(newData)
    img.save(input_path, "PNG")

if __name__ == "__main__":
    icons_dir = Path("C:/Users/Friends shop/OneDrive/Desktop/BOQ ESTOMATION/HVAC_Project/data/icons")
    
    print("Converting white backgrounds to transparent...")
    # List of names we just renamed to
    names = ['S-60', 'CR-60', 'S-30', 'CR-30', 'S-15', 'CR-15', 'PC', 'HWS', 'HWR', 'GHS', 'GHR', 'SWS', 'SWR', 'RL', 'RS', 'RHG', 'CWS', 'CWR', 'CHS', 'CHR', 'GCS', 'GCR', 'MW', 'D', 'V', 'GRS', 'GRR', 'X']
    
    count = 0
    for name in names:
        f = icons_dir / f"{name}.png"
        if f.exists():
            make_transparent(f)
            count += 1
            print(f" [OK] {name}.png is now transparent")
            
    print(f"Total processed: {count} files")
