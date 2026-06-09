"""
🎯 KAGGLE TRAINING NOTEBOOK — HVAC Symbol Detection
====================================================
Copy this EXACTLY into Kaggle cells
"""

# ============ CELL 1 — Install & Import ============
!pip install ultralytics opencv-python -q

from ultralytics import YOLO
import os
import shutil
import yaml

print("GPU Status:")
os.system("nvidia-smi")

# ============ CELL 2 — Verify Data ============
import os
dataset_path = '/kaggle/input/hvac-final-clean'
print(f"Dataset contents:")
print(os.listdir(dataset_path))
print(f"\nTrain images: {len(os.listdir(f'{dataset_path}/images/train'))}")
print(f"Val images: {len(os.listdir(f'{dataset_path}/images/val'))}")
print(f"Train labels: {len(os.listdir(f'{dataset_path}/labels/train'))}")
print(f"Val labels: {len(os.listdir(f'{dataset_path}/labels/val'))}")

# ============ CELL 3 — Fix YAML Path ============
# Kaggle paths are different from local — fix them
with open(f'{dataset_path}/data.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update to Kaggle paths
data['path'] = dataset_path
data['train'] = 'images/train'
data['val'] = 'images/val'

print("\nData YAML:")
print(yaml.dump(data))

# Save to working directory
with open('/kaggle/working/data.yaml', 'w') as f:
    yaml.dump(data, f)

# ============ CELL 4 — Load Fresh Model ============
# CRITICAL: Use yolo11s.pt (fresh, not old last.pt)
print("Loading fresh YOLOv11s model...")
model = YOLO('yolo11s.pt')
print(f"Model loaded: {model}")

# ============ CELL 5 — TRAIN ============
# This is the MOST IMPORTANT CELL
# All settings optimized for 60 small images + small symbols

print("\n" + "="*70)
print("🚀 STARTING TRAINING")
print("="*70 + "\n")

results = model.train(
    data='/kaggle/working/data.yaml',
    
    # === BASIC ===
    epochs=100,
    imgsz=640,
    batch=16,          # Reduce to 8 if CUDA OOM
    
    # === LEARNING RATE ===
    lr0=0.005,         # Lower LR for small dataset
    lrf=0.0001,        # Final LR (very low)
    warmup_epochs=5,   # Warm up for 5 epochs
    
    # === OPTIMIZATION ===
    optimizer='SGD',   # More stable than Adam for small data
    momentum=0.937,
    weight_decay=0.0005,
    
    # === LOSS WEIGHTS (CRITICAL FOR SMALL SYMBOLS) ===
    box=7.5,           # ← HIGH: Small objects need strong box loss
    cls=0.5,           # ← FOCAL LOSS: Handles class imbalance
    dfl=1.5,           # Distribution focal loss for tiny objects
    
    # === AUGMENTATION (HEAVY — only 60 images!) ===
    degrees=15,
    translate=0.1,
    scale=0.5,         # Zoom 0.5x to 1.5x
    shear=2,
    perspective=0.0,
    flipud=0.3,        # Vertical flip
    fliplr=0.5,        # Horizontal flip
    
    # === MOSAIC (creates 4x diversity from 60 images) ===
    mosaic=1.0,        # ← ON (always for small dataset)
    mixup=0.2,         # Blend 2 images
    copy_paste=0.1,    # Copy symbols between images
    
    # === AUGMENTATION STRINGS ===
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    
    # === EARLY STOPPING ===
    patience=30,       # Don't stop early (small dataset needs full training)
    
    # === SAVING ===
    save=True,
    save_period=10,    # Save checkpoint every 10 epochs
    project='/kaggle/working/runs',
    name='hvac_v1',
    exist_ok=True,
    
    # === VALIDATION ===
    val=True,
    split=0.0,         # Use our 85/15 split (NOT random)
    
    # === DEVICE ===
    device=0,          # GPU 0
    
    # === VERBOSITY ===
    verbose=True,
)

print("\n" + "="*70)
print("✅ TRAINING COMPLETE!")
print("="*70)

# ============ CELL 6 — Evaluate ============
print("\n📊 Final Metrics:\n")

# Validate
metrics = model.val()

print(f"mAP50:     {metrics.box.map50:.4f}")
print(f"mAP50-95:  {metrics.box.map:.4f}")
print(f"Precision: {metrics.box.mp:.4f}")
print(f"Recall:    {metrics.box.mr:.4f}")

# ============ CELL 7 — Check Results ============
import matplotlib.pyplot as plt
from PIL import Image

# Show training curves
results_img = Image.open('/kaggle/working/runs/hvac_v1/results.png')
plt.figure(figsize=(15, 5))
plt.imshow(results_img)
plt.axis('off')
plt.title('Training Results')
plt.tight_layout()
plt.show()

# ============ CELL 8 — Save Best Model ============
print("Saving best.pt...")
shutil.copy(
    '/kaggle/working/runs/hvac_v1/weights/best.pt',
    '/kaggle/working/best.pt'
)
print("✅ best.pt saved to /kaggle/working/")

# ============ CELL 9 — Test on Sample ============
# Load best model
best_model = YOLO('/kaggle/working/best.pt')

# Test on one validation image
val_imgs = os.listdir('/kaggle/input/hvac-final-clean/images/val')
if val_imgs:
    test_img_path = f'/kaggle/input/hvac-final-clean/images/val/{val_imgs[0]}'
    
    results = best_model.predict(test_img_path, conf=0.25, imgsz=640)
    
    print(f"\nTest predictions on {val_imgs[0]}:")
    print(f"Detections: {len(results[0].boxes)}")
    
    # Show
    from IPython.display import Image as IPImage
    IPImage(filename=results[0].save(filename='/kaggle/working/test_result.jpg')[0])
