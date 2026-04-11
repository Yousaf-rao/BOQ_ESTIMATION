# Phase 2: AI Brain Integration — Complete Implementation Plan

**Project:** HVAC BOQ Estimation System  
**Phase:** 2 of 5 — "The Brain" (AI Vision Integration)  
**Date:** April 2, 2026  
**Prerequisite:** Phase 1 COMPLETE

---

## Phase 1 Analysis (What We Already Have)

| Asset | File | Details |
|:---|:---|:---|
| PDF Converter | `day2_pdf_to_image.py` | Converts A0/A1 CAD PDFs to 288 DPI images via PyMuPDF |
| Legend Extractor | `day4_legend_extractor.py` | Crops right 22% of drawing as legend reference |
| Overlap Tiler | `day6_overlap_tiling.py` | Generates 1200x1200px tiles with 300px overlap |
| Full Pipeline | `day7_full_pipeline.py` | HVACVisionEngine class runs all steps end-to-end |
| Config | `config.py` | Centralized settings (zoom=4.0, tile=1200, overlap=300) |
| Legend Image | `data/legends/legend_reference.png` | 876 KB cropped legend/title block |
| Legend Map | `data/legend_map.json` | 18 HVAC symbol abbreviations to full names |
| Tile Map | `data/output_tiles/_tile_map.json` | 20 tiles with exact (x,y) coordinates |
| Tiles | `data/output_tiles/*.png` | 20 PNG files (142KB to 845KB each) |

### Key Technical Facts
- Source image: 7439 x 6736 pixels
- Total tiles: 20 (non-blank, after filtering)
- Tile naming: tile_y{Y}_x{X}.png (coordinates in filename)
- Overlap: 300px (step = 900px) — critical for de-duplication
- Legend: Contains symbol dictionary for AI reference
- legend_map.json: 18 entries (SCD, RCD, SD, RD, SA, RA, EA, OA, VAV, FCU, AHU, H, C, TSTAT, FD, VCD, BD)

---

## Phase 2 Architecture Overview

```
                  PHASE 2 PIPELINE

   legend_reference.png ---+
   legend_map.json --------+
                           |
                           v
   +------------------------------+
   |   SYSTEM PROMPT BUILDER      |  <-- Day 8
   |   (Role + Schema + Rules)    |
   +----------+-------------------+
              |
              v
   +------------------------------+
   |   GEMINI API CLIENT          |  <-- Day 9
   |   (Auth + Multimodal Call)   |
   +----------+-------------------+
              |
              v
   +------------------------------+
   |   TILE PROCESSOR             |  <-- Day 10
   |   (Loop all 20 tiles)        |
   |   Legend + Tile -> AI -> JSON|
   +----------+-------------------+
              |
              v
   +------------------------------+
   |   RESPONSE PARSER            |  <-- Day 11
   |   (Validate + Clean JSON)    |
   +----------+-------------------+
              |
              v
   +------------------------------+
   |   RESULTS AGGREGATOR         |  <-- Day 12
   |   (Merge 20 tile results)    |
   +----------+-------------------+
              |
              v
       raw_counts.json (per tile)
       merged_counts.json (building total)
```

---

## Day 8: Environment Setup + System Prompt Design

### Task 8.1 — Install Gemini SDK
```
pip install google-generativeai python-dotenv pillow
```

### Task 8.2 — API Key Configuration
- Create `.env` file (already in .gitignore):
  ```
  GEMINI_API_KEY=your_key_here
  ```
- Update `config.py` to load the key securely

### Task 8.3 — System Prompt Design
Create file: `prompts/system_prompt.txt`
Must contain:
1. Role definition — "You are a Senior HVAC Estimation Engineer..."
2. Legend context — Loaded from legend_map.json
3. Task instruction — "Identify and count HVAC symbols in this tile"
4. Output schema — Exact JSON structure
5. Rules — "Do NOT guess. If unsure, set confidence to low"

### Task 8.4 — JSON Response Schema
```json
{
  "tile_id": "tile_y0_x2700",
  "symbols_found": [
    {
      "symbol_code": "SCD",
      "symbol_name": "Supply Ceiling Diffuser",
      "count": 4,
      "confidence": "high",
      "size_label": "600x600",
      "notes": ""
    }
  ],
  "text_labels_detected": ["200x200 L/A", "REV-03"],
  "has_ductwork": true,
  "tile_quality": "good"
}
```

**Output:** prompts/system_prompt.txt, updated config.py

---

## Day 9: Gemini API Client (Single Tile Test)

### Task 9.1 — Create gemini_client.py
```python
class GeminiHVACClient:
    def __init__(self):
        # Load API key from config
        # Initialize Gemini model
        # Load system prompt
    
    def analyze_tile(self, tile_path, legend_path):
        # Send legend + tile as multimodal input
        # Return parsed JSON response
    
    def _build_prompt(self, legend_context):
        # Combine system prompt + legend_map data
```

### Task 9.2 — Multimodal Input Function
Send TWO images to Gemini simultaneously:
- Image A: legend_reference.png (the symbol dictionary)
- Image B: One tile (e.g., tile_y2700_x3600.png)
- Text: System prompt with JSON schema

### Task 9.3 — Single Tile Test
- Pick densest tile: tile_y2700_x3600.png (845 KB — most HVAC symbols)
- Run against Gemini and verify JSON output
- Save raw response to data/test_responses/

### Task 9.4 — Error Handling & Retry Logic
- Handle: API rate limits (429), timeout, invalid JSON
- Implement: Exponential backoff retry (max 3 attempts)
- Log: Every API call with timestamp, tile_id, response time

**Output:** gemini_client.py

---

## Day 10: Tile Batch Processor (All 20 Tiles)

### Task 10.1 — Create tile_processor.py
```python
class TileProcessor:
    def __init__(self):
        # Load _tile_map.json
        # Initialize GeminiHVACClient
    
    def process_all_tiles(self):
        # Loop through all 20 tiles
        # Send each tile + legend to Gemini
        # Track progress (5/20, 10/20, etc.)
    
    def process_single_tile(self, tile_info):
        # Process one tile entry
```

### Task 10.2 — Progress Tracking & Cost Control
- Rate limiting: 2-second delay between API calls
- Progress display: "Processing tile 7/20: tile_y1800_x3600.png..."
- Cost tracking: Log token usage per call
- Resume capability: Skip already-processed tiles on re-run

### Task 10.3 — Per-Tile Result Storage
```
data/ai_results/
  tile_y0_x2700_result.json
  tile_y0_x3600_result.json
  ... (20 files)
```

**Output:** tile_processor.py, data/ai_results/*.json

---

## Day 11: Response Validator + Parser

### Task 11.1 — Create response_parser.py
```python
class ResponseParser:
    def validate_response(self, raw_response):
        # Check valid JSON, required fields
    
    def normalize_symbol_names(self, symbols):
        # Match AI output to legend_map.json
        # "Supply Diffuser" -> "SCD"
    
    def flag_low_confidence(self, symbols):
        # Separate high vs low confidence items
```

### Task 11.2 — Symbol Name Normalization
AI might say different names for the same symbol:
```
AI says: "Ceiling Diffuser"    -> Map to: "SCD"
AI says: "Supply Air Diffuser" -> Map to: "SCD"
```
Build fuzzy matching using legend_map.json as reference.

### Task 11.3 — Confidence Scoring
- HIGH — Count directly
- MEDIUM — Include but flag for review
- LOW — Exclude from final count, send to human review

### Task 11.4 — Validation Report
Generate _validation_report.json with processing statistics.

**Output:** response_parser.py

---

## Day 12: Results Aggregator (Merge All Tiles)

### Task 12.1 — Create results_aggregator.py
```python
class ResultsAggregator:
    def merge_tile_results(self):
        # Load all 20 per-tile JSONs
        # Sum symbol counts across tiles
    
    def generate_summary(self):
        # Create _merged_counts.json
        # Group by category
```

### Task 12.2 — Category Grouping
```json
{
  "Air Terminals": {
    "SCD (Supply Ceiling Diffuser)": 24,
    "RCD (Return Ceiling Diffuser)": 18
  },
  "Dampers": {
    "VCD (Volume Control Damper)": 12,
    "FD (Fire Damper)": 6
  },
  "Equipment": {
    "FCU (Fan Coil Unit)": 8,
    "AHU (Air Handling Unit)": 2
  }
}
```

**Output:** results_aggregator.py, data/ai_results/_merged_counts.json

---

## Day 13: Phase 2 Full Pipeline Integration

### Task 13.1 — Create phase2_brain_engine.py
```python
class HVACBrainEngine:
    def run_full_phase2(self):
        # Step 1: Load Phase 1 outputs
        # Step 2: Initialize Gemini client
        # Step 3: Process all tiles
        # Step 4: Validate responses
        # Step 5: Aggregate results
        # Step 6: Generate summary report
```

### Task 13.2 — End-to-End Test
```
Input:  20 tiles + legend + legend_map.json
Output: merged_counts.json (building-level BOQ)
```

### Task 13.3 — Console Report
Professional summary with symbol counts, confidence metrics, and timing.

**Output:** phase2_brain_engine.py

---

## New File Structure After Phase 2

```
HVAC_Project/
  config.py                    (updated with Gemini settings)
  .env                         (API key — gitignored)
  day2_pdf_to_image.py         (Phase 1)
  day4_legend_extractor.py     (Phase 1)
  day5_basic_tiling.py         (Phase 1)
  day6_overlap_tiling.py       (Phase 1)
  day7_full_pipeline.py        (Phase 1 master)
  gemini_client.py             <-- NEW (Day 9)
  tile_processor.py            <-- NEW (Day 10)
  response_parser.py           <-- NEW (Day 11)
  results_aggregator.py        <-- NEW (Day 12)
  phase2_brain_engine.py       <-- NEW (Day 13)
  prompts/
    system_prompt.txt           <-- NEW (Day 8)
  data/
    legends/legend_reference.png
    legend_map.json
    output_tiles/_tile_map.json + 20 tiles
    ai_results/                 <-- NEW
      tile_*_result.json        (20 per-tile results)
      _validation_report.json
      _merged_counts.json
    test_responses/             <-- NEW (Day 9 testing)
```

---

## Cost Estimation (Gemini 1.5 Pro)

| Item | Estimate |
|:---|:---|
| Tiles per drawing | 20 |
| Images per call | 2 (legend + tile) |
| Cost per call | ~$0.005 |
| Total per drawing | ~$0.10 |
| Time per drawing | ~2-3 minutes |

TIP: Start with gemini-1.5-flash for testing (10x cheaper).
Switch to gemini-1.5-pro for production accuracy.

---

## Summary Checklist

| Day | Task | Creates | Status |
|:---|:---|:---|:---|
| Day 8 | Environment + Prompt Design | .env, prompts/system_prompt.txt | Not Started |
| Day 9 | Gemini API Client + Single Test | gemini_client.py | Not Started |
| Day 10 | Batch Tile Processing | tile_processor.py | Not Started |
| Day 11 | Response Validation + Parsing | response_parser.py | Not Started |
| Day 12 | Results Aggregation | results_aggregator.py | Not Started |
| Day 13 | Full Pipeline + E2E Test | phase2_brain_engine.py | Not Started |

IMPORTANT: Before starting Day 8, you need a Gemini API key.
Get it free from: https://aistudio.google.com/apikey

---

Prepared by: Antigravity AI
For: HVAC BOQ Estimation Project Team
