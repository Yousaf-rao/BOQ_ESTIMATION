# **🔥 HVAC DETECTION MASTER PLAN**
## **24 Real CAD Drawings → Working AI Model**

---

## **📊 DEEP ANALYSIS (Why Old Model Failed)**

| **Problem** | **What Happened** | **Why** |
| :--- | :--- | :--- |
| **Scale** | 14,000×10,000 drawing → symbols 2px at training | Invisible to model |
| **Domain** | Trained on transparent icons → tested on white paper | Different worlds |
| **Classes** | 186 fake classes vs 11 real classes | Brain confusion |
| **Data** | 2400 fake + 0 real = 0% real exposure | Never saw real CAD |

**Result:** 0 detections on real drawings.

**Solution:** Start fresh with **ONLY real data**.

---

## **✅ PHASE 1: PREPARE TILES (Your PC — 30 minutes) 🎯 [TODAY'S WORK]**

### **What You Need**
- 24 labeled images from Roboflow (exported as **YOLO v11**)
- Python installed on your PC

### **Steps**

#### **Step 1.1: Export from Roboflow**
1. Login to **Roboflow.com**
2. Open your **HVAC_BOQ** project
3. Click **"Export Dataset"**
4. Select format: **YOLO v11**
5. Download the ZIP file
6. Extract ZIP to your Downloads folder
7. You will see: `train/images/` (24 JPG files) and `train/labels/` (24 TXT files)

#### **Step 1.2: Run Tile Generator Script**
1. Open the file: `tile_yolo_dataset.py` inside `HVAC_Project/`
2. Run: `python HVAC_Project/tile_yolo_dataset.py`
3. Wait 1-2 minutes
4. Output folder created: `real_tiled_dataset/`

**What happens inside:**
- Each large drawing is cut into **640×640** small pieces
- **20% overlap** between tiles (so symbols at edges don't get cut)
- Labels automatically adjust for each small piece
- Empty tiles are automatically skipped to keep training dataset clean
- Result: **38 training images** generated from your real drawings

#### **Step 1.3: Make ZIP File**
1. Run: `python HVAC_Project/create_zip.py`
2. Output file created: `real_tiled_kaggle.zip` in your main folder.

---

## **✅ PHASE 2: UPLOAD TO KAGGLE (Kaggle.com — 15 minutes)**

### **What You Need**
- Kaggle account (free)
- `real_tiled_kaggle.zip` from Phase 1

### **Steps**

#### **Step 2.1: Create Dataset on Kaggle**
1. Go to **Kaggle.com** → Login
2. Click **"Datasets"** in the left menu
3. Click button **"New Dataset"**
4. Title: `hvac-real-tiles`
5. Click **"Upload"** → Select your `real_tiled_kaggle.zip`
6. Click **"Create"**

#### **Step 2.2: Create Notebook**
1. Go to **Kaggle.com → Notebooks**
2. Click **"New Notebook"**
3. On right side panel:
   - **Accelerator**: Select **GPU T4 x2** (IMPORTANT!)
   - **Language**: Python
4. Click **Save**

#### **Step 2.3: Add Your Dataset**
1. Right side panel → **"Add Data"**
2. Click **"Your Datasets"**
3. Find: `hvac-real-tiles`
4. Click **"Add"**
5. Your data is now inside the notebook at: `/kaggle/input/hvac-real-tiles/`

---

## **✅ PHASE 3: TRAIN MODEL (Kaggle GPU — 1-3 hours)**

### **What You Need**
- Notebook ready with dataset added
- 6 code cells (from `Kaggle_Training_Notebook.py`)

### **Steps**

#### **Step 3.1: Copy Code Cells**
Open `Kaggle_Training_Notebook.py` on your PC, copy each cell to Kaggle:

- **CELL 1**: Install `ultralytics`
- **CELL 2**: Verify paths
- **CELL 3**: Create fixed `data.yaml` for Kaggle directories
- **CELL 4**: Load fresh model (`yolo11s.pt` — official trained model, NOT your old model)
- **CELL 5**: Train model (100 Epochs, imgsz=640, batch=16, device=0)
- **CELL 6**: Save the best weights as `HVAC_real_best.pt`

#### **Step 3.2: Run Training**
1. Click **"Run All"** in Kaggle
2. Check training progress. It will run on Kaggle servers (you can close your browser).

---

## **✅ PHASE 4: DOWNLOAD & TEST (Your PC — 30 minutes)**

### **Steps**
1. Go to Kaggle Notebook **"Output"** tab
2. Download `HVAC_real_best.pt`
3. Run predictions on your real CAD drawings at `conf=0.25`
