# HVAC AI BOQ Estimation Pipeline - Technical Architecture
**Type:** Context Document for LLM / Code Generation
**Project Name:** AI HVAC BOQ Estimator

This document provides complete context on the architecture, file structure, workflows, and algorithmic approaches used in the HVAC AI BOQ Project. Feed this to any code-generating LLM (like DeepSeek) before asking it to write or modify code for this project.

---

## 1. Project Objective & Core Strategy
The goal is to automate identifying, counting, and generating a Bill of Quantities (BOQ) for HVAC symbols (Return Diffusers, Supply Diffusers, Exhaust VAVs, etc.) from standard PDF engineering floor plans.

**Why AI over Traditional OpenCV?**
Classic Template matching (`cv2.matchTemplate`) fails due to symbol scaling, rotation, and overlapping ductwork/wires. Therefore, we use **Vision Large Multimodal Models (LMMs)** for cognitive detection. We feed a small segment (tile) of the master floor plan along with the legend map to the AI and ask it to output bounding boxes for recognized symbols.

---

## 2. Tech Stack & APIs
*   **Language:** Python 3.x
*   **Image Processing:** `OpenCV` (`cv2`), `NumPy`, `Pillow`
*   **Core AI Engine:** Groq API (Running Meta Llama Vision models)
    *   *Primary Model:* `llama-3.2-90b-vision-preview` (Higher accuracy for tiny symbols)
    *   *Fallback Model:* `meta-llama/llama-4-scout-17b-16e-instruct`
*   **Rate Limits:** Script relies on exponential backoffs and physical delays (`time.sleep`) to prevent HTTP 429 errors from free tier limits.
*   **Data Serialization:** Strict JSON structures (`base64` for image transfer to API).

---

## 3. The End-to-End Workflow

**Phase 1: Pre-Processing (Image Preparation)**
1.  **PDF to Image:** High-resolution rendering to ensure symbols aren't blurred.
2.  **Legend Extraction:** Slicing the right-hand panel (Title Block) to isolate symbol definitions. AI scans this to create `legend_map.json` (Key: "SCD", Value: "Supply Ceiling Diffuser").
3.  **Overlap Tiling:** A massive 6000x8000 floor plan crashes APIs. The image is cut into overlapping tiles (e.g., 1024x1024 px with 10% overlap) ensuring no symbol is sliced at an exact boundary. This creates `_spatial_tile_map.json`.

**Phase 2: The "Smart Brain" Engine (Current Focus)**
1.  **Smart Spatial Runner (`spatial_detector.py`):**
    *   **Ink Filtering (OpenCV):** Checks if the tile is just empty white space (detects `black_pixels < 200` threshold). If dark pixels are `< 1%`, it completely skips hitting the AI. This saves 60% of API limits.
    *   **AI Scan:** Submits the Legend + the ink-filtered Tile to Llama Vision on Groq. Asks for bounding box `[ymin, xmin, ymax, xmax]` coordinates of exact symbol classes.
    *   **Rate Limit Recovery:** If it gets a `429 Too Many Requests`, it initiates a hard 60s/120s/180s cooldown and retries.
    *   **Resume Capability:** Constantly flushes arrays to `partial_results.json` so interrupted tasks can resume exactly where they crashed.

**Phase 3: Aggregation & Deduplication (`results_aggregator.py`)**
Because tiles overlap by 10%, a symbol sitting on the boundary gets detected *twice* (once in Tile 1, once in Tile 2). 
*   **IoU (Intersection over Union):** The script parses global coordinates and merges boxes that heavily overlap using IoU thresholds > 0.3.

---

## 4. Key Files & Structure

*   **`config.py`**
    *   The SINGLE source of truth for all paths, API keys, thresholds (Tile sizes, IoU limits, etc.). Modifying constants should only occur here.
*   **`gemini_client.py` (Misnomer, runs Groq API)**
    *   Abstracts the AI calls (`GeminiHVACClient` class). Handles base64 conversion and structured JSON enforcement (`response_format={"type": "json_object"}`).
*   **`spatial_detector.py`**
    *   The main iterative loop over the JSON tile map. Contains the OpenCV ink filter and robust retry logic.
*   **`response_parser.py` & `results_aggregator.py`**
    *   Pulls bounding boxes out of AI responses, applies deduplication algorithms, counts final totals, and generates output tables.

---

## 5. Rules for DeepSeek Code Generation (Important Constraints)

1.  **DO NOT Modify AI Schema without need:** The Llama Vision model requires explicit multi-modal JSON requests (an array containing `image_url` object dictionaries mapping to `data:image/png;base64,...`). Do not accidentally override this strict schema.
2.  **Use `config.py`:** If you are configuring a new delay, a threshold, or a path, add it to `config.py` and import it. Do NOT hardcode `1024` or `path/to/folder` strings inside scripts.
3.  **JSON Strictness:** Whenever prompting the Llama model, ALWAYS ensure `response_format={"type": "json_object"}` is used in the SDK call, and include "Return JSON format only" in the prompt string.
4.  **Acknowledge the Scale:** HVAC engineering drawings have very high resolution. OpenCV bounding box mappings (`[ymin, xmin, ymax, xmax]`) must be normalized back to the original image dimensions carefully.
5.  **Logging & Resiliency:** Operations take 5-15 minutes. Always stream clear progress in the console (Current Tile, Total Detection, Sleep States) and use `partial_results.json` techniques to support killing and resuming the scripts safely.
