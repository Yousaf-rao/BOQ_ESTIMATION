# ============================================================================
# results_aggregator.py — Day 12: Results Aggregator (Merge All Tiles)
# ============================================================================
#
# 🎯 OBJECTIVE: 20 tiles ke results ko MERGE karke EK BOQ banao!
#   Har tile ka apna JSON result hai. Ab sab ko jodna hai.
#
# REAL-WORLD ANALOGY:
#   Imagine karo 20 junior engineers ne 20 zones count kiye.
#   Har ek ne apni list banayi. Ab SENIOR (yeh code) sab lists
#   ko merge karega aur final BOQ (Bill of Quantities) banayega.
#
# KEY CHALLENGES:
#   1. DEDUPLICATION — Overlapping tiles mein ek symbol 2 baar aa sakta hai
#      Solution: overlap_risk=true wale symbols ko handle karna
#   2. CATEGORY GROUPING — SCD, RCD → "Air Terminals" category
#   3. CONFIDENCE FILTER — Low confidence items alag rakhna
#
# OUTPUT:
#   data/ai_results/_merged_counts.json — Building-level BOQ
#
# 📝 HOW TO RUN:  python results_aggregator.py
# ============================================================================

import os
import sys
import json
import time
import logging
from datetime import datetime
from collections import defaultdict

# --------------------------------------------------------------------------
# defaultdict: Python ki special dictionary hai.
#   Normal dict mein agar key nahi hai toh error aata hai.
#   defaultdict mein agar key nahi hai toh AUTOMATIC default value ban jaati hai.
#
#   Example:
#     counts = defaultdict(int)    # Default = 0
#     counts["SCD"] += 5           # SCD pehle nahi thi, but 0+5 = 5 ✅
# --------------------------------------------------------------------------

from config import CONFIG

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ============================================================================
# CATEGORY MAPPING — HVAC symbols ko categories mein group karna
# ============================================================================
# BOQ mein items category-wise hote hain:
#   - "Air Terminals" = Diffusers, Grilles, Registers (jahan se hawa aati/jaati hai)
#   - "Dampers" = Flow control devices (hawa ki speed/direction control)
#   - "Equipment" = Major equipment (FCU, AHU, EF, etc.)
#   - "Controls & Sensors" = Smart devices (Thermostat, CO2 sensor, DDC)
#   - "Duct Accessories" = Duct ke saath lagne wali cheezein
#
# Yeh mapping real EPC project BOQ format follow karti hai.
# ============================================================================

CATEGORY_MAP = {
    # ── Air Terminals (Diffusers, Grilles, Registers) ──
    "SCD": "Air Terminals",       # Supply Ceiling Diffuser
    "RCD": "Air Terminals",       # Return Ceiling Diffuser
    "ECD": "Air Terminals",       # Exhaust Ceiling Diffuser
    "SLD": "Air Terminals",       # Supply Linear Diffuser
    "RLD": "Air Terminals",       # Return Linear Diffuser
    "EDV": "Air Terminals",       # Exhaust Disc Valve
    "DG":  "Air Terminals",       # Door Grille
    "RR":  "Air Terminals",       # Return Register
    "BMO": "Air Terminals",       # Bell Mouth Opening
    
    # ── Dampers ──
    "VD":  "Dampers",             # Volume Damper
    "FSD": "Dampers",             # Fire Smoke Damper
    "BDD": "Dampers",             # Back Draft Damper
    "MVD": "Dampers",             # Motorized Volume Damper
    
    # ── Equipment ──
    "FCU": "Equipment",           # Fan Coil Unit
    "VAV": "Equipment",           # Variable Air Volume
    "RTU": "Equipment",           # Roof Top Unit
    "EF":  "Equipment",           # Exhaust Fan
    "EDH": "Equipment",           # Electric Duct Heater
    
    # ── Controls & Sensors ──
    "T":   "Controls & Sensors",  # Thermostat
    "CO2": "Controls & Sensors",  # CO2 Sensor
    "DDC": "Controls & Sensors",  # Direct Digital Control
    
    # ── Duct Accessories ──
    "TD":  "Duct Accessories",    # Transfer Duct
    "RP":  "Duct Accessories",    # Refrigerant Pipe
}


class ResultsAggregator:
    """
    Saari tiles ke results ko merge karke building-level BOQ banata hai.
    
    YEH CLASS KYA KARTI HAI:
        1. LOAD — Saari per-tile result JSON files load karo
        2. MERGE — Symbol counts jodho (with deduplication)
        3. CATEGORIZE — Symbols ko BOQ categories mein group karo
        4. SUMMARIZE — Final counts aur statistics banao
        5. SAVE — _merged_counts.json file save karo
    
    DEDUPLICATION LOGIC:
        Overlapping tiles mein ek symbol 2 baar count ho sakta hai.
        
        APPROACH (conservative):
        - "overlap_risk: false" → Full count (bharosa hai unique hai)
        - "overlap_risk: true"  → 50% count (half credit — kyunke
          dono adjacent tiles mein dikhega, toh average lo)
        
        Yeh 100% accurate nahi hai, but ek REASONABLE estimate hai.
        Future improvement: coordinate-based exact deduplication.
    """
    
    def __init__(self):
        """
        Aggregator initialize karo.
        
        STEPS:
            1. Legend map load karo (symbol names ke liye)
            2. Results directory set karo
            3. Merged data structures banao
        """
        
        print("\n  📊 Initializing Results Aggregator...")
        
        # ------------------------------------------------------------------
        # Legend Map (for descriptions)
        # ------------------------------------------------------------------
        self.legend_map = self._load_legend_map()
        
        # ------------------------------------------------------------------
        # Paths
        # ------------------------------------------------------------------
        self.results_dir = CONFIG["AI_RESULTS_DIR"]
        
        # ------------------------------------------------------------------
        # Merged Data — yahan sab tiles ka combined data aayega
        # ------------------------------------------------------------------
        # defaultdict(int) = automatic 0 se start hone wali dictionary
        # counts["SCD"] += 3 → pehli baar 0+3=3, doosri baar 3+5=8
        self.symbol_counts = defaultdict(int)        # Code → total quantity
        self.symbol_sizes = defaultdict(list)         # Code → list of all sizes found
        self.symbol_flow_rates = defaultdict(list)    # Code → list of all flow rates
        self.overlap_deductions = defaultdict(float)  # Code → deducted overlap count
        
        # Per-tile tracking
        self.tile_results = []  # Saari tiles ke loaded results
        self.failed_tiles = []  # Tiles jinke results nahi mile
        
        print("  📊 Results Aggregator ready!\n")
    
    # ======================================================================
    # PUBLIC METHODS
    # ======================================================================
    
    def merge_tile_results(self):
        """
        Saari per-tile JSON results load karo aur merge karo.
        
        FLOW:
            1. data/ai_results/ se saari *_result.json files load karo
            2. Har file ka symbols array lo
            3. Symbol counts jodho
            4. Overlap deduplication apply karo
        
        Returns:
            dict: Merged symbol counts
        """
        
        print("  📥 Loading per-tile results...")
        
        # ------------------------------------------------------------------
        # STEP 1: Result files dhundho aur load karo
        # ------------------------------------------------------------------
        if not os.path.exists(self.results_dir):
            print(f"  ❌ Results directory not found: {self.results_dir}")
            print(f"  👉 Run Day 10 first to process all tiles")
            return {}
        
        # Sirf *_result.json files lo, _merged ya _validation ko skip karo
        result_files = sorted([
            f for f in os.listdir(self.results_dir)
            if f.endswith("_result.json") and not f.startswith("_")
        ])
        
        if not result_files:
            print(f"  ❌ No result files found in {self.results_dir}")
            print(f"  👉 Run Day 10 first to process all tiles")
            return {}
        
        print(f"  ✅ Found {len(result_files)} result files")
        
        # ------------------------------------------------------------------
        # STEP 2: Har file load karo aur symbols extract karo
        # ------------------------------------------------------------------
        for filename in result_files:
            filepath = os.path.join(self.results_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.tile_results.append(data)
                
                # Symbols process karo
                symbols = data.get("symbols", [])
                
                for symbol in symbols:
                    code = symbol.get("code", "UNKNOWN")
                    quantity = symbol.get("quantity", 0)
                    instances = symbol.get("instances", [])
                    confidence = symbol.get("confidence", "medium")
                    
                    # ---- Confidence Filter ----
                    # LOW confidence wale exclude karo final count se
                    if confidence == "low":
                        continue
                    
                    # ---- Overlap Deduplication ----
                    # Har instance check karo — overlap_risk hai ya nahi?
                    for instance in instances:
                        overlap_risk = instance.get("overlap_risk", False)
                        
                        if overlap_risk:
                            # OVERLAP RISK hai — 50% credit do
                            # Kyunke yeh symbol adjacent tile mein bhi hoga
                            # Dono tiles 50% count karengi → total = 100%
                            self.symbol_counts[code] += 0.5
                            self.overlap_deductions[code] += 0.5
                        else:
                            # No overlap risk — full count
                            self.symbol_counts[code] += 1
                        
                        # Size collect karo (unique sizes track karne ke liye)
                        size = instance.get("size")
                        if size:
                            self.symbol_sizes[code].append(size)
                        
                        # Flow rate collect karo
                        flow_rate = instance.get("flow_rate_lps")
                        if flow_rate is not None:
                            self.symbol_flow_rates[code].append(flow_rate)
                
                print(f"     ✅ {filename}: {len(symbols)} symbol types")
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"     ❌ {filename}: Error — {e}")
                self.failed_tiles.append(filename)
                logging.error(f"Failed to load {filename}: {e}")
        
        # ------------------------------------------------------------------
        # STEP 3: Round final counts (0.5s ko handle karo)
        # ------------------------------------------------------------------
        # 2.5 → 3 (round up — conservative approach — miss karne se acha zyada count)
        import math
        for code in self.symbol_counts:
            self.symbol_counts[code] = math.ceil(self.symbol_counts[code])
        
        print(f"\n  ✅ Merge complete: {len(self.symbol_counts)} unique symbol types")
        
        return dict(self.symbol_counts)
    
    def generate_summary(self):
        """
        Building-level BOQ summary banao — categories ke saath.
        
        OUTPUT FORMAT:
            {
                "Air Terminals": {
                    "SCD (Supply Ceiling Diffuser)": 24,
                    "RCD (Return Ceiling Diffuser)": 18
                },
                "Dampers": {
                    "VD (Volume Damper)": 12,
                    ...
                },
                ...
            }
        
        Returns:
            dict: Category-grouped BOQ summary
        """
        
        print("\n  📋 Generating BOQ Summary...")
        
        # ------------------------------------------------------------------
        # STEP 1: Category-wise Grouping
        # ------------------------------------------------------------------
        # defaultdict(dict) = automatic empty dictionary banata hai har category ke liye
        categorized = defaultdict(dict)
        uncategorized = {}
        
        for code, count in sorted(self.symbol_counts.items()):
            # Description dhundho legend map se
            description = self.legend_map.get(code, "UNKNOWN")
            
            # Category dhundho
            category = CATEGORY_MAP.get(code, None)
            
            # Display label banao: "SCD (Supply Ceiling Diffuser)"
            label = f"{code} ({description})"
            
            if category:
                categorized[category][label] = count
            else:
                uncategorized[label] = count
        
        # Agar kuch uncategorized hain toh alag category mein rakho
        if uncategorized:
            categorized["Uncategorized"] = uncategorized
        
        # ------------------------------------------------------------------
        # STEP 2: Size Summary Banao
        # ------------------------------------------------------------------
        # Har symbol ke liye unique sizes ki list
        size_summary = {}
        for code, sizes in self.symbol_sizes.items():
            unique_sizes = sorted(set(sizes))
            description = self.legend_map.get(code, code)
            size_summary[f"{code} ({description})"] = {
                "unique_sizes": unique_sizes,
                "most_common": max(set(sizes), key=sizes.count) if sizes else None,
            }
        
        # ------------------------------------------------------------------
        # STEP 3: Complete Summary Compile Karo
        # ------------------------------------------------------------------
        grand_total = sum(self.symbol_counts.values())
        
        summary = {
            "report_title": "HVAC Bill of Quantities — Building Level",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "grand_total_items": grand_total,
            "tiles_processed": len(self.tile_results),
            "tiles_failed": len(self.failed_tiles),
            
            # Main BOQ — category-wise counts
            "boq_by_category": dict(categorized),
            
            # Flat counts — sab symbols ek list mein
            "flat_counts": {
                f"{code} ({self.legend_map.get(code, 'UNKNOWN')})": count
                for code, count in sorted(
                    self.symbol_counts.items(),
                    key=lambda x: x[1],
                    reverse=True  # Zyada wale pehle
                )
            },
            
            # Size details
            "size_details": size_summary,
            
            # Overlap deductions
            "overlap_adjustments": {
                code: round(ded, 1)
                for code, ded in self.overlap_deductions.items()
                if ded > 0
            },
            
            # Category totals
            "category_totals": {
                cat: sum(items.values())
                for cat, items in categorized.items()
            },
        }
        
        # ------------------------------------------------------------------
        # STEP 4: Save karo
        # ------------------------------------------------------------------
        self._save_merged_counts(summary)
        self._print_boq_report(summary)
        
        return summary
    
    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================
    
    def _load_legend_map(self):
        """Legend map JSON load karo."""
        map_path = CONFIG["LEGEND_MAP_PATH"]
        
        if not os.path.exists(map_path):
            print(f"  ⚠️  Legend map not found, using empty map")
            return {}
        
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_merged_counts(self, summary):
        """
        Merged BOQ ko _merged_counts.json mein save karo.
        """
        
        output_path = os.path.join(self.results_dir, "_merged_counts.json")
        
        os.makedirs(self.results_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n  💾 Saved: _merged_counts.json")
        logging.info(f"Merged counts saved: {output_path}")
    
    def _print_boq_report(self, summary):
        """
        Console pe professional BOQ report print karo.
        
        Yeh report client meeting mein dikhane ke laiq honi chahiye!
        """
        
        print(f"\n{'🔷' * 30}")
        print(f"  📋 HVAC BILL OF QUANTITIES — BUILDING LEVEL")
        print(f"{'🔷' * 30}")
        print(f"  Generated: {summary['generated_at']}")
        print(f"  Tiles processed: {summary['tiles_processed']}")
        print(f"  Grand total items: {summary['grand_total_items']}")
        
        # Category-wise display
        boq = summary.get("boq_by_category", {})
        
        for category, items in boq.items():
            category_total = sum(items.values())
            print(f"\n  ┌─ {category} ({category_total} items)")
            print(f"  │")
            
            for label, count in sorted(items.items(), key=lambda x: x[1], reverse=True):
                # Bar chart banao (visual representation)
                bar = "█" * min(count, 40)  # Max 40 chars ka bar
                print(f"  │  {label:45s} : {count:4d}  {bar}")
            
            print(f"  └─")
        
        # Overlap adjustments
        adjustments = summary.get("overlap_adjustments", {})
        if adjustments:
            print(f"\n  ⚠️  Overlap Deductions Applied:")
            for code, ded in adjustments.items():
                desc = self.legend_map.get(code, code)
                print(f"     {code} ({desc}): -{ded} (from overlapping tiles)")
        
        print(f"\n{'🔷' * 30}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 12: RESULTS AGGREGATOR")
    print("=" * 60)
    
    # ------------------------------------------------------------------
    # Check ke AI results exist karti hain
    # ------------------------------------------------------------------
    results_dir = CONFIG["AI_RESULTS_DIR"]
    
    if not os.path.exists(results_dir):
        print(f"\n  ❌ No AI results found at: {results_dir}")
        print(f"  👉 Run Day 10 first to process all tiles")
        print(f"\n  💡 Creating demo data for testing...")
        
        # Demo data banao testing ke liye (agar actual results nahi hain)
        os.makedirs(results_dir, exist_ok=True)
        
        demo_result = {
            "tile_id": "demo_tile.png",
            "symbols": [
                {"code": "SCD", "description": "SUPPLY CEILING DIFFUSER",
                 "quantity": 3, "confidence": "high",
                 "instances": [
                     {"size": "600x600", "flow_rate_lps": 250,
                      "position": "center", "overlap_risk": False},
                     {"size": "450x450", "flow_rate_lps": 180,
                      "position": "center", "overlap_risk": False},
                     {"size": "600x600", "flow_rate_lps": 200,
                      "position": "edge", "overlap_risk": True},
                 ]},
                {"code": "VD", "description": "VOLUME DAMPER",
                 "quantity": 1, "confidence": "high",
                 "instances": [
                     {"size": "300x200", "flow_rate_lps": None,
                      "position": "center", "overlap_risk": False},
                 ]},
                {"code": "FCU", "description": "FAN COIL UNIT",
                 "quantity": 1, "confidence": "medium",
                 "instances": [
                     {"size": None, "flow_rate_lps": None,
                      "position": "center", "overlap_risk": False},
                 ]},
            ],
        }
        
        demo_path = os.path.join(results_dir, "demo_tile_result.json")
        with open(demo_path, 'w') as f:
            json.dump(demo_result, f, indent=2)
        print(f"  ✅ Demo data created: demo_tile_result.json")
    
    # ------------------------------------------------------------------
    # Aggregate!
    # ------------------------------------------------------------------
    aggregator = ResultsAggregator()
    
    # Step 1: Merge
    counts = aggregator.merge_tile_results()
    
    if counts:
        # Step 2: Summary
        summary = aggregator.generate_summary()
    else:
        print(f"\n  ⚠️  No results to aggregate")
    
    print(f"\n  🎉 DAY 12 COMPLETE!")
    print("=" * 60)
