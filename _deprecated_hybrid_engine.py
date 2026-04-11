# ============================================================================
# hybrid_engine.py — Hybrid 2.0: Evidence-Based HVAC Vision Engine
# ============================================================================
#
# 🎯 OBJECTIVE:
#   OpenCV ki "Geometric Precision" + Groq Vision AI ki "Semantic Intelligence"
#   ko mil kar 100% accurate BOQ generate karna.
#
# ARCHITECTURE:
#   MODULE A — SCOUT    : OpenCV Template Matching (Geometry Detection)
#   MODULE B — PATCHER  : 120x120 "Evidence Patches" crop karna
#   MODULE C — VALIDATOR: Groq Vision AI se Binary Yes/No validation
#   MODULE D — BOQ      : Deduplicate + Excel export
#
# HOW TO RUN:
#   python hybrid_engine.py
#
# PREREQUISITES:
#   1. Run day7_full_pipeline.py (floor_plan_only.png generate karo)
#   2. Run template_extractor.py (data/templates/ mein icons save karo)
# ============================================================================

import cv2
import os
import json
import time
import base64
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from groq import Groq

from config import CONFIG

# ─────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
DRAWING_PATH     = os.path.join(BASE_DIR, "data", "floor_plan_only.png")
TEMPLATES_DIR    = os.path.join(BASE_DIR, "data", "templates")
PATCHES_DIR      = os.path.join(BASE_DIR, "data", "evidence_patches")
RESULTS_DIR      = os.path.join(BASE_DIR, "data", "hybrid_results")
EXCEL_OUTPUT     = os.path.join(BASE_DIR, "Hybrid_BOQ_Report.xlsx")

# OpenCV thresholds
SCOUT_THRESHOLD  = 0.45    # Lowered: 45% similarity (legend vs drawing zip scale differ)
PATCH_SIZE       = 150     # 150x150 pixel evidence patch
DEDUP_DISTANCE   = 60      # 60px ke andar duplicate ko ignore karo

# Multi-scale matching — drawing ki zoom level ke liye (wide range)
SCALES = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 1.8, 2.0]
DEBUG_MODE = True  # Save heatmap images for diagnosis

# Logging
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    filename=os.path.join(BASE_DIR, "logs", "hybrid_engine.log"),
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)


# ============================================================================
# MODULE A: SCOUT — OpenCV Template Matching
# ============================================================================

class Scout:
    """
    OpenCV se symbols ki geometry dhoondhta hai.
    Ye sirf "potential locations" deta hai — AI baad mein confirm karega.
    """

    def __init__(self, drawing_path, templates_dir):
        print(f"\n  🔭 [SCOUT] Loading floor plan...")
        self.img_color = cv2.imread(drawing_path)
        if self.img_color is None:
            raise FileNotFoundError(f"Drawing not found: {drawing_path}")

        self.img_gray = cv2.cvtColor(self.img_color, cv2.COLOR_BGR2GRAY)
        self.templates_dir = templates_dir
        h, w = self.img_color.shape[:2]
        print(f"     Drawing size: {w} x {h} px")
        logging.info(f"Scout initialized: {w}x{h} drawing")

    def scan_all_templates(self):
        """
        Templates folder ke har icon ko drawing mein dhoondhta hai.

        Returns:
            list of dicts:
            [{"code": "SCD", "cx": 450, "cy": 890, "score": 0.78, "template_path": ...}, ...]
        """
        all_detections = []
        templates = [f for f in os.listdir(self.templates_dir)
                     if f.endswith(".png") and not f.startswith("_")]

        print(f"     Templates to scan: {len(templates)}")

        for tname in templates:
            code = tname.replace(".png", "")
            tpath = os.path.join(self.templates_dir, tname)
            template = cv2.imread(tpath, cv2.IMREAD_GRAYSCALE)

            if template is None:
                print(f"     ⚠️  Cannot load template: {tname}")
                continue

            detections = self._multi_scale_match(template, code, tpath)
            all_detections.extend(detections)
            print(f"     🔍 {code:8s}: {len(detections)} raw hits")

        print(f"\n     Total raw detections: {len(all_detections)}")
        return all_detections

    def _multi_scale_match(self, template, code, tpath):
        """
        Multiple scales pe template match karo.
        Drawing mein symbols kabhi thore chhote ya bare ho sakte hain.
        """
        detections = []
        th, tw = template.shape[:2]

        for scale in SCALES:
            scaled_w = int(tw * scale)
            scaled_h = int(th * scale)

            if scaled_w < 5 or scaled_h < 5:
                continue

            resized = cv2.resize(template, (scaled_w, scaled_h))
            result = cv2.matchTemplate(self.img_gray, resized, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= SCOUT_THRESHOLD)

            for pt in zip(*loc[::-1]):
                cx = pt[0] + scaled_w // 2
                cy = pt[1] + scaled_h // 2
                score = float(result[pt[1], pt[0]])
                detections.append({
                    "code": code,
                    "cx": int(cx),
                    "cy": int(cy),
                    "score": round(score, 3),
                    "scale": scale,
                    "template_path": tpath
                })

        # NMS (Non-Maximum Suppression): ek jagah ke paas ke duplicates hatao
        return self._nms(detections)

    def _nms(self, detections, dist=40):
        """
        Ek hi jagah ke multiple overlapping detections mein se sirf best (highest score) rakho.
        """
        if not detections:
            return []

        detections.sort(key=lambda d: d["score"], reverse=True)
        kept = []

        for det in detections:
            is_dup = False
            for existing in kept:
                dx = abs(det["cx"] - existing["cx"])
                dy = abs(det["cy"] - existing["cy"])
                if dx < dist and dy < dist:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(det)

        return kept


# ============================================================================
# MODULE B: PATCHER — Evidence Patches Crop Karna
# ============================================================================

class Patcher:
    """
    Har detection ke liye 120x120 px "Evidence Patch" crop karta hai.
    AI ke liye sirf ye chhota patch bheja jayega — poori drawing nahi!
    """

    def __init__(self, img_color, patches_dir):
        self.img = img_color
        self.patches_dir = patches_dir
        os.makedirs(patches_dir, exist_ok=True)
        self.h, self.w = img_color.shape[:2]

    def create_patch(self, detection, idx):
        """
        Ek detection ke center ke around 120x120 patch crop karo.

        Returns:
            str: Saved patch path, ya None agar fail ho
        """
        cx, cy = detection["cx"], detection["cy"]
        half = PATCH_SIZE // 2

        # Boundaries (image se bahar na jaye)
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(self.w, cx + half)
        y2 = min(self.h, cy + half)

        patch = self.img[y1:y2, x1:x2].copy()

        # Patch naam: verify_SCD_001.png
        code = detection["code"]
        score_str = str(int(detection["score"] * 100))
        patch_name = f"verify_{code}_{idx:04d}_s{score_str}.png"
        patch_path = os.path.join(self.patches_dir, patch_name)

        cv2.imwrite(patch_path, patch)
        return patch_path

    def create_all_patches(self, detections):
        """
        Saari detections ke patches banao.

        Returns:
            detections list with 'patch_path' added
        """
        print(f"\n  ✂️  [PATCHER] Creating {len(detections)} evidence patches...")

        for i, det in enumerate(detections):
            patch_path = self.create_patch(det, i)
            det["patch_path"] = patch_path

        print(f"     Patches saved to: {self.patches_dir}")
        return detections


# ============================================================================
# MODULE C: VALIDATOR — Groq Vision AI Binary Validation
# ============================================================================

class Validator:
    """
    Groq Vision AI se har patch ko validate karta hai.
    Binary question: "Kya ye waqai SCD hai? Yes/No"
    """

    def __init__(self):
        api_key = CONFIG["GROQ_API_KEY"]
        if not api_key:
            raise ValueError("GROQ_API_KEY missing in .env!")
        self.client = Groq(api_key=api_key)
        self.model = CONFIG.get("GROQ_MODEL", "llama-3.2-90b-vision-preview")
        print(f"\n  🤖 [VALIDATOR] Groq client ready | Model: {self.model}")
        self.stats = {"validated": 0, "confirmed": 0, "rejected": 0, "errors": 0}

    def _img_to_b64(self, path):
        """Image file → base64 string"""
        from PIL import Image as PILImage
        import io
        img = PILImage.open(path)
        img.thumbnail((300, 300), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def validate(self, detection):
        """
        Ek patch ko validate karo: icon + patch dono AI ko bhejo.

        Returns:
            dict: {"is_match": bool, "confidence": float, "size_tag": str/None, "room": str/None}
        """
        code = detection["code"]
        patch_path = detection.get("patch_path")
        icon_path = detection.get("template_path")

        if not patch_path or not os.path.exists(patch_path):
            return {"is_match": False, "confidence": 0, "size_tag": None, "room": None}

        prompt = f"""TASK: MECHANICAL VALIDATION — Zero-hallucination mode.

You are comparing two images:
1. [MASTER ICON]: The reference symbol for "{code}" from the HVAC legend.
2. [EVIDENCE PATCH]: A 120x120 cropped area from the actual floor plan.

STRICT RULES:
- Return is_match=true ONLY if the geometric shape in the patch matches the master icon.
- If the patch is just lines, duct walls, text, or empty background → is_match=false.
- If is_match=true, extract size_tag (e.g. "600x600", "150x150") if visible near the symbol.
- Extract room name if visible near the symbol.
- DO NOT guess. If unsure → is_match=false.

OUTPUT: STRICT JSON ONLY — No explanation, no text outside JSON.
{{"is_match": true/false, "confidence": 0.0-1.0, "size_tag": "string or null", "room": "string or null"}}"""

        for attempt in range(3):
            try:
                icon_b64 = self._img_to_b64(icon_path) if icon_path and os.path.exists(icon_path) else None
                patch_b64 = self._img_to_b64(patch_path)

                content = []
                if icon_b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{icon_b64}"}})
                    content.append({"type": "text", "text": "↑ MASTER ICON (Reference from Legend)"})

                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{patch_b64}"}})
                content.append({"type": "text", "text": f"↑ EVIDENCE PATCH (Cropped from floor plan)\n\n{prompt}"})

                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": content}],
                    temperature=0.0,
                    max_tokens=256,
                )

                raw = response.choices[0].message.content
                result = json.loads(raw)

                self.stats["validated"] += 1
                if result.get("is_match"):
                    self.stats["confirmed"] += 1
                else:
                    self.stats["rejected"] += 1

                return result

            except Exception as e:
                logging.warning(f"Validator attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)

        self.stats["errors"] += 1
        return {"is_match": False, "confidence": 0, "size_tag": None, "room": None}

    def validate_all(self, detections, max_per_code=50):
        """
        Saari detections validate karo.
        max_per_code: Ek code ke liye max kitne patches check karein (API save)
        """
        print(f"\n  🔬 [VALIDATOR] Validating {len(detections)} detections...")
        print(f"     (Max {max_per_code} per symbol type to save API calls)")

        code_counts = {}
        validated = []

        for i, det in enumerate(detections):
            code = det["code"]
            code_counts[code] = code_counts.get(code, 0) + 1

            # Skip agar too many already validated for this code
            if code_counts[code] > max_per_code:
                continue

            print(f"     [{i+1:03d}/{len(detections)}] Validating {code} at ({det['cx']}, {det['cy']})...", end=" ")
            result = self.validate(det)

            det.update(result)
            validated.append(det)

            status = "✅ MATCH" if result.get("is_match") else "❌ REJECT"
            tag = result.get("size_tag") or ""
            conf = result.get("confidence", 0)
            print(f"{status} (conf={conf:.2f}) {tag}")

            # Groq rate limit ke liye thoda wait
            time.sleep(1.5)

        print(f"\n     Confirmed: {self.stats['confirmed']} | Rejected: {self.stats['rejected']} | Errors: {self.stats['errors']}")
        return validated


# ============================================================================
# MODULE D: BOQ COMPILER — Deduplicate + Excel Export
# ============================================================================

class BOQCompiler:
    """
    Validated detections ko final BOQ Excel mein compile karta hai.
    Global deduplication: tile overlap mein same symbol dobara count nahi hoga.
    """

    MARKET_RATES = {
        "SCD": 6500,  "RCD": 6500,  "VD": 2500,   "VAV": 45000,
        "EDV": 1800,  "EDH": 35000, "FSD": 8500,   "DG": 4500,
        "BMO": 2000,  "SLD": 8000,  "CO2": 15000,  "TD": 4000,
        "RR": 3500,   "RLD": 8000,  "BDD": 3000,   "T": 5000,
    }

    LEGEND_MAP = {
        "SCD": "SUPPLY CEILING DIFFUSER",   "RCD": "RETURN CEILING DIFFUSER",
        "EDV": "EXHAUST DISC VALVE",        "SLD": "SUPPLY LINEAR DIFFUSER",
        "RLD": "RETURN LINEAR DIFFUSER",    "T":   "THERMOSTAT",
        "CO2": "CO2 SENSOR",                "VD":  "VOLUME DAMPER",
        "FSD": "FIRE SMOKE DAMPER",         "VAV": "VARIABLE AIR VOLUME",
        "BDD": "BACK DRAFT DAMPER",         "BMO": "BELL MOUTH OPENING",
        "DG":  "DOOR GRILLE",               "EDH": "ELECTRIC DUCT HEATER",
        "RR":  "RETURN REGISTER",           "TD":  "TRANSFER DUCT",
    }

    def __init__(self, results_dir, excel_path):
        self.results_dir = results_dir
        self.excel_path = excel_path
        os.makedirs(results_dir, exist_ok=True)

    def deduplicate(self, validated_detections, dist=DEDUP_DISTANCE):
        """
        Global coordinate-based deduplication.
        Agar do detections ek hi code ke hain aur 50px ke andar → ek hi count hoga.
        """
        print(f"\n  🔄 [BOQ] Deduplicating {len(validated_detections)} confirmed matches...")

        confirmed = [d for d in validated_detections if d.get("is_match")]

        # Group by code
        by_code = {}
        for det in confirmed:
            code = det["code"]
            by_code.setdefault(code, []).append(det)

        final_detections = []
        for code, dets in by_code.items():
            kept = []
            for det in dets:
                is_dup = False
                for existing in kept:
                    dx = abs(det["cx"] - existing["cx"])
                    dy = abs(det["cy"] - existing["cy"])
                    if dx < dist and dy < dist:
                        is_dup = True
                        break
                if not is_dup:
                    kept.append(det)
            print(f"     {code:8s}: Before={len(dets):3d}  After dedup={len(kept):3d}")
            final_detections.extend(kept)

        print(f"     Total unique symbols: {len(final_detections)}")
        return final_detections

    def compile_to_excel(self, final_detections):
        """Final BOQ Excel export karo."""

        # Group by code for summary
        summary = {}
        for det in final_detections:
            code = det["code"]
            if code not in summary:
                summary[code] = {"count": 0, "sizes": [], "coords": []}
            summary[code]["count"] += 1
            if det.get("size_tag"):
                summary[code]["sizes"].append(det["size_tag"])
            summary[code]["coords"].append(f"({det['cx']},{det['cy']})")

        # Build DataFrame
        rows = []
        for code, info in summary.items():
            qty = info["count"]
            size = max(set(info["sizes"]), key=info["sizes"].count) if info["sizes"] else "Varied"
            rate = self.MARKET_RATES.get(code, 5000)
            desc = self.LEGEND_MAP.get(code, code)
            rows.append({
                "Code": code,
                "Description": desc,
                "Size (Most Common)": size,
                "Unit": "No.",
                "Hybrid AI Qty": qty,
                "Unit Rate (PKR)": rate,
                "Total Amount (PKR)": qty * rate,
                "Method": "OpenCV + AI Verified",
            })

        df = pd.DataFrame(rows).sort_values("Total Amount (PKR)", ascending=False)

        writer = pd.ExcelWriter(self.excel_path, engine="xlsxwriter")
        df.to_excel(writer, sheet_name="Hybrid BOQ", index=False)

        wb  = writer.book
        ws  = writer.sheets["Hybrid BOQ"]

        hdr = wb.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1, "align": "center"})
        mny = wb.add_format({"num_format": "#,##0", "border": 1})
        ctr = wb.add_format({"align": "center", "border": 1})
        grn = wb.add_format({"bold": True, "bg_color": "#E2EFDA", "num_format": "#,##0", "border": 1})

        ws.set_column("A:A", 10, ctr)
        ws.set_column("B:B", 35, ctr)
        ws.set_column("C:C", 18, ctr)
        ws.set_column("D:D", 8,  ctr)
        ws.set_column("E:E", 15, ctr)
        ws.set_column("F:F", 16, mny)
        ws.set_column("G:G", 20, mny)
        ws.set_column("H:H", 22, ctr)

        for col, val in enumerate(df.columns):
            ws.write(0, col, val, hdr)

        total_row = len(df) + 1
        ws.write(total_row, 5, "GRAND TOTAL", hdr)
        ws.write_formula(total_row, 6, f"=SUM(G2:G{total_row})", grn)

        writer.close()

        grand_total = df["Total Amount (PKR)"].sum()
        print(f"\n  📊 [BOQ] Excel Report Generated!")
        print(f"     File   : {self.excel_path}")
        print(f"     Items  : {len(df)}")
        print(f"     GRAND TOTAL: PKR {grand_total:,.0f}")

        return df, grand_total


# ============================================================================
# MASTER RUNNER
# ============================================================================

def run_hybrid_pipeline():
    print("=" * 65)
    print("  🚀 HYBRID 2.0 — Evidence-Based HVAC Vision Engine")
    print("=" * 65)

    start = time.time()

    # ── Prereq checks ──────────────────────────────────────────
    if not os.path.exists(DRAWING_PATH):
        print(f"\n  ❌ Drawing not found: {DRAWING_PATH}")
        print(f"  👉 Run: python day7_full_pipeline.py")
        return

    templates = [f for f in os.listdir(TEMPLATES_DIR)
                 if f.endswith(".png") and not f.startswith("_")]
    if not templates:
        print(f"\n  ❌ No templates in: {TEMPLATES_DIR}")
        print(f"  👉 Run: python template_extractor.py")
        return

    print(f"\n  ✅ Drawing  : {os.path.basename(DRAWING_PATH)}")
    print(f"  ✅ Templates: {len(templates)} icons ready → {[t.replace('.png','') for t in templates]}")

    # ─────────────────────────────────────────
    # MODULE A: SCOUT
    # ─────────────────────────────────────────
    scout = Scout(DRAWING_PATH, TEMPLATES_DIR)
    raw_detections = scout.scan_all_templates()

    if not raw_detections:
        print("\n  ⚠️  No geometric matches found!")
        print("  💡 Try lowering SCOUT_THRESHOLD in hybrid_engine.py (e.g., 0.55)")
        return

    # ─────────────────────────────────────────
    # MODULE B: PATCHER
    # ─────────────────────────────────────────
    patcher = Patcher(scout.img_color, PATCHES_DIR)
    detections_with_patches = patcher.create_all_patches(raw_detections)

    # ─────────────────────────────────────────
    # MODULE C: VALIDATOR
    # ─────────────────────────────────────────
    validator = Validator()
    validated = validator.validate_all(detections_with_patches, max_per_code=30)

    # Save raw validated JSON
    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_path = os.path.join(RESULTS_DIR, "hybrid_validated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Raw results saved: {json_path}")

    # ─────────────────────────────────────────
    # MODULE D: BOQ COMPILER
    # ─────────────────────────────────────────
    compiler = BOQCompiler(RESULTS_DIR, EXCEL_OUTPUT)
    final = compiler.deduplicate(validated)
    df, grand_total = compiler.compile_to_excel(final)

    # ─────────────────────────────────────────
    # FINAL SUMMARY
    # ─────────────────────────────────────────
    elapsed = time.time() - start
    print(f"\n{'=' * 65}")
    print(f"  ✅ HYBRID 2.0 PIPELINE COMPLETE")
    print(f"{'=' * 65}")
    print(f"  Raw Detections (OpenCV)  : {len(raw_detections)}")
    print(f"  After AI Validation      : {validator.stats['confirmed']}")
    print(f"  After Deduplication      : {len(final)}")
    print(f"  Grand Total (PKR)        : {grand_total:,.0f}")
    print(f"  Total Time               : {elapsed:.1f}s")
    print(f"  Excel Report             : {EXCEL_OUTPUT}")
    print(f"{'=' * 65}")
    logging.info(f"Hybrid pipeline done: {len(final)} confirmed | PKR {grand_total:,.0f} | {elapsed:.1f}s")


if __name__ == "__main__":
    run_hybrid_pipeline()
