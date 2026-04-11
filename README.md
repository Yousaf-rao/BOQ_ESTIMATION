# HVAC BOQ Estimation — AI Vision Pipeline

> **Automated Bill of Quantities (BOQ) estimation from HVAC engineering drawings using computer vision and large language models.**

---

## Project Overview

This project processes HVAC floor-plan PDFs and automatically:

1. **Extracts symbols** from legend pages (PDF → PNG icons)
2. **Generates synthetic training data** (YOLO-annotated images) from those icons
3. **Detects symbols** on floor-plan tiles using AI vision (Gemini / DeepSeek)
4. **Aggregates counts** and exports a professional Excel BOQ report

---

## Project Structure

```
HVAC_Project/
├── generate_synthetic_data.py   # Phase 2 – synthetic dataset generator
├── day1_setup.py                # Environment validation
├── day2_pdf_to_image.py         # PDF → high-res PNG conversion
├── day3_opencv_basics.py        # OpenCV preprocessing helpers
├── day4_legend_extractor.py     # Legend symbol extraction
├── day5_basic_tiling.py         # Floor-plan tiling
├── day6_overlap_tiling.py       # Overlap-aware tiling
├── day7_full_pipeline.py        # End-to-end orchestration
├── gemini_client.py             # Gemini 1.5 Pro AI client
├── deepseek_client.py           # DeepSeek-VL2 AI client (fallback)
├── phase2_brain_engine.py       # AI symbol counting engine
├── phase3_excel_exporter.py     # Excel BOQ report exporter
├── spatial_detector.py          # Template-matching spatial detector
├── response_parser.py           # AI response JSON parser
├── results_aggregator.py        # Cross-tile result aggregation
├── config.py                    # Central configuration
├── data/
│   ├── icons/                   # Extracted HVAC symbol PNGs (417 icons)
│   ├── dataset/                 # Generated YOLO training dataset
│   │   ├── classes.txt          # 23 HVAC symbol classes
│   │   ├── dataset.yaml         # YOLOv8 config
│   │   └── class_mapping.json   # Class ID ↔ name mapping
│   ├── legends/                 # Extracted legend templates
│   ├── classes.txt              # Master class list
│   └── legend_map.json          # Symbol abbreviation → full name
├── docs/                        # Implementation plans & notes
└── prompts/                     # AI prompt templates
```

---

## Phase 2 — Synthetic Data Generation

The `generate_synthetic_data.py` script generates YOLO-annotated training images by compositing HVAC icons onto realistic CAD drawing backgrounds.

### Features
- **413 icons** organised into **23 classes** from your legend pages
- **4 background types**: engineering grid, blueprint, clean white, worn paper
- **Smart augmentation**: random scale, rotation (prefers 0°/90°/180°/270°), brightness, contrast
- **Correct alpha blending** for white-background icons
- **Overlap control** via IoU threshold
- **Built-in verifier** checks all image–label pairs and YOLO format

### Usage

```bash
# Generate 3000 training images (default)
python generate_synthetic_data.py

# Generate 5000 images
python generate_synthetic_data.py --num-images 5000

# Verify an existing dataset only
python generate_synthetic_data.py --mode verify

# Custom paths
python generate_synthetic_data.py --icons path/to/icons --output path/to/out
```

### Dataset Output

| Split  | Images | Objects |
|--------|--------|---------|
| Train  | 2 400  | ~10 800 |
| Val    |   450  |  ~2 000 |
| Test   |   150  |    ~650 |
| **Total** | **3 000** | **~13 500** |

---

## Setup

```bash
pip install opencv-python pillow numpy pyyaml tqdm
pip install google-generativeai openai python-dotenv
pip install PyMuPDF pdf2image openpyxl
```

Copy `.env.example` → `.env` and add your API keys:

```
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here   # optional, for DeepSeek
```

---

## Symbol Classes (23)

| ID | Class | ID | Class |
|----|-------|----|-------|
| 0  | check_valve | 12 | page_16_symbol |
| 1  | gate_valve_hose | 13 | page_17_symbol |
| 2  | gate_valve_threaded | 14 | page_18_symbol |
| 3  | globe_valve_threaded | 15 | page_6_symbol |
| 4  | page_10_symbol | 16 | page_7_symbol |
| 5  | page_11_symbol | 17 | page_8_symbol |
| 6  | page_12_line_symbol | 18 | page_9_symbol |
| 7  | page_12_symbol | 19 | wye_strainer_ball_valve |
| 8  | page_13_line_symbol | 20 | wye_strainer_ball_valve_hose |
| 9  | page_13_symbol | 21 | wye_strainer_drain |
| 10 | page_14_symbol | 22 | wye_strainer_valvedDraing_quickCouple |
| 11 | page_15_symbol | | |

---

## License

MIT
