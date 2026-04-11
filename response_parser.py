# ============================================================================
# response_parser.py — Day 11: Response Validator + Parser
# ============================================================================
#
# 🎯 OBJECTIVE: Gemini ke AI responses ko VALIDATE aur CLEAN karna!
#   AI kabhi kabhi galat naam deti hai, wrong format deti hai,
#   ya low confidence results deti hai. Yeh file sab ko handle karti hai.
#
# REAL-WORLD ANALOGY:
#   Sochiye ek junior engineer ne quantities nikali hain.
#   Senior engineer (yeh code) un quantities ko CHECK karta hai:
#   - Kya format sahi hai?
#   - Kya symbol names legend se match karti hain?
#   - Kya kisi result pe bharosa kam hai?
#
# KEY FEATURES:
#   ✅ JSON Response Validation (required fields check)
#   ✅ Symbol Name Normalization (AI ke different names → standard codes)
#   ✅ Fuzzy Matching (AI kehtā hai "Ceiling Diffuser" → match to "SCD")
#   ✅ Confidence Scoring & Filtering (high/medium/low segregation)
#   ✅ Validation Report Generation
#
# 📝 HOW TO RUN (standalone test):
#   python response_parser.py
# ============================================================================

import os
import sys
import json
import time
import logging
from datetime import datetime

# --------------------------------------------------------------------------
# difflib: Python ki built-in library hai — strings ki similarity check
# karne ke liye. "Fuzzy matching" ke liye use hoti hai.
#
# FUZZY MATCHING KYA HAI?
#   Exact match: "SCD" == "SCD" ✅
#   Fuzzy match: "Supply Ceiling Diffuser" ≈ "SUPPLY CEILING DIFFUSER" ✅
#   AI kabhi kabhi exact code nahi deti, full name deti hai.
#   Fuzzy matching se hum usko sahi code se match kar lete hain.
# --------------------------------------------------------------------------
from difflib import SequenceMatcher

from config import CONFIG

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(CONFIG["LOG_FILE"]), exist_ok=True)
logging.basicConfig(
    filename=CONFIG["LOG_FILE"], level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ResponseParser:
    """
    AI ke responses ko validate, clean, aur normalize karta hai.
    
    YEH CLASS KYA KARTI HAI:
        1. VALIDATE — Check karo ke JSON structure sahi hai
        2. NORMALIZE — AI ke different names ko standard codes mein convert karo
        3. FILTER — Low confidence items alag karo (human review ke liye)
        4. REPORT — Validation statistics ka report banao
    
    WHY IS THIS NEEDED?
        AI (Gemini/GPT) bahut smart hai, but kabhi kabhi:
        - "Ceiling Diffuser" likhti hai instead of "SCD"
        - "Supply Air Diffuser" likhti hai instead of "SCD"
        - Confidence "low" hoti hai but phir bhi count kar deti hai
        - JSON structure change kar deti hai
        
        Yeh class in SARI problems ko handle karti hai!
    """
    
    def __init__(self):
        """
        Parser initialize karo — legend map load karo aur lookup tables banao.
        
        STEPS:
            1. Legend map load karo (SCD → SUPPLY CEILING DIFFUSER)
            2. Reverse map banao (SUPPLY CEILING DIFFUSER → SCD)
            3. Fuzzy matching ke liye searchable list banao
        """
        
        print("\n  🔍 Initializing Response Parser...")
        
        # ------------------------------------------------------------------
        # STEP 1: Legend Map Load Karo
        # ------------------------------------------------------------------
        # {"SCD": "SUPPLY CEILING DIFFUSER", "VD": "VOLUME DAMPER", ...}
        self.legend_map = self._load_legend_map()
        
        # ------------------------------------------------------------------
        # STEP 2: Reverse Map Banao
        # ------------------------------------------------------------------
        # Normal map:  code → name   ("SCD" → "SUPPLY CEILING DIFFUSER")
        # Reverse map: name → code   ("SUPPLY CEILING DIFFUSER" → "SCD")
        # 
        # Yeh tab kaam aata hai jab AI full name deti hai code ki jagah
        self.reverse_map = {
            name.upper(): code 
            for code, name in self.legend_map.items()
        }
        
        # ------------------------------------------------------------------
        # STEP 3: Valid Codes ki Set Banao
        # ------------------------------------------------------------------
        # Set = Python mein unique values ka collection
        # "in" check bahut fast hota hai set mein (O(1) vs O(n) for list)
        self.valid_codes = set(self.legend_map.keys())
        
        # ------------------------------------------------------------------
        # STEP 4: Non-countable labels ki list
        # ------------------------------------------------------------------
        # Yeh directional/unit labels hain — equipment NAHI hain
        # AI in ko symbol samajh sakti hai, but yeh countable nahi hain
        self.non_countable = {"T/A", "T/B", "F/A", "F/B", "LPS", "N.C"}
        
        # ------------------------------------------------------------------
        # Validation Stats
        # ------------------------------------------------------------------
        self.validation_stats = {
            "total_responses_validated": 0,
            "valid_responses": 0,
            "invalid_responses": 0,
            "symbols_normalized": 0,
            "symbols_removed_non_countable": 0,
            "low_confidence_flagged": 0,
            "fuzzy_matches": [],         # Record: kya match hua
            "unrecognized_symbols": [],   # AI ne kuch aisa diya jo legend mein nahi
        }
        
        print(f"  ✅ Legend map loaded: {len(self.legend_map)} valid codes")
        print(f"  ✅ Non-countable labels: {self.non_countable}")
        print("  🔍 Response Parser ready!\n")
    
    # ======================================================================
    # PUBLIC METHODS
    # ======================================================================
    
    def validate_response(self, raw_response):
        """
        AI response ki JSON structure check karo — required fields hain ya nahi?
        
        Parameters:
            raw_response: dict — Parsed JSON response from Gemini
        
        Returns:
            tuple: (is_valid: bool, errors: list, warnings: list)
        
        CHECKS:
            1. Top-level keys present hain? (tile_id, symbols, etc.)
            2. symbols array hai ya nahi?
            3. Har symbol mein code, quantity, instances hain?
            4. quantity == len(instances)?
        """
        
        self.validation_stats["total_responses_validated"] += 1
        
        errors = []    # Yeh woh issues hain jo MUST fix hain
        warnings = []  # Yeh minor issues hain — acceptable but noted
        
        if not isinstance(raw_response, dict):
            errors.append("Response is not a JSON object (dictionary)")
            self.validation_stats["invalid_responses"] += 1
            return False, errors, warnings
        
        # ------------------------------------------------------------------
        # CHECK 1: Top-level required fields
        # ------------------------------------------------------------------
        # Yeh fields humara system_prompt.txt mein define hain
        required_fields = ["tile_id", "symbols"]
        
        for field in required_fields:
            if field not in raw_response:
                errors.append(f"Missing required field: '{field}'")
        
        # Optional but expected fields — agar nahi hain toh warn karo
        optional_fields = ["duct_runs_detected", "tile_quality", 
                          "warnings", "requires_human_review"]
        
        for field in optional_fields:
            if field not in raw_response:
                warnings.append(f"Missing optional field: '{field}'")
        
        # ------------------------------------------------------------------
        # CHECK 2: symbols array hai?
        # ------------------------------------------------------------------
        symbols = raw_response.get("symbols", [])
        
        if not isinstance(symbols, list):
            errors.append("'symbols' must be an array/list")
        else:
            # ------------------------------------------------------------------
            # CHECK 3: Har symbol ki structure check karo
            # ------------------------------------------------------------------
            for i, symbol in enumerate(symbols):
                prefix = f"symbols[{i}]"
                
                if not isinstance(symbol, dict):
                    errors.append(f"{prefix}: Not a valid object")
                    continue
                
                # Required symbol fields
                if "code" not in symbol:
                    errors.append(f"{prefix}: Missing 'code'")
                
                if "quantity" not in symbol:
                    errors.append(f"{prefix}: Missing 'quantity'")
                
                if "instances" not in symbol:
                    errors.append(f"{prefix}: Missing 'instances'")
                
                # ------------------------------------------------------------------
                # CHECK 4: quantity == len(instances)
                # ------------------------------------------------------------------
                # Rule 8 from system_prompt.txt:
                # "quantity" MUST equal len(instances)
                if "quantity" in symbol and "instances" in symbol:
                    qty = symbol["quantity"]
                    inst_count = len(symbol.get("instances", []))
                    
                    if qty != inst_count:
                        warnings.append(
                            f"{prefix}: quantity={qty} but instances count={inst_count}. "
                            f"Auto-correcting quantity to {inst_count}"
                        )
                        # Auto-correct — instances ki count pe bharosa karo
                        symbol["quantity"] = inst_count
                
                # Confidence check
                confidence = symbol.get("confidence", "medium")
                if confidence not in ("high", "medium", "low"):
                    warnings.append(
                        f"{prefix}: Invalid confidence '{confidence}'. Setting to 'medium'"
                    )
                    symbol["confidence"] = "medium"
        
        # ------------------------------------------------------------------
        # RESULT
        # ------------------------------------------------------------------
        is_valid = len(errors) == 0
        
        if is_valid:
            self.validation_stats["valid_responses"] += 1
        else:
            self.validation_stats["invalid_responses"] += 1
        
        return is_valid, errors, warnings
    
    def normalize_symbol_names(self, response):
        """
        AI ke symbol codes/names ko standard legend_map codes mein convert karo.
        
        PROBLEM:
            AI might say different things for the same symbol:
            - "Ceiling Diffuser"        → Should be: "SCD"
            - "Supply Air Diffuser"     → Should be: "SCD"  
            - "SUPPLY CEILING DIFFUSER" → Should be: "SCD"
            - "scd"                     → Should be: "SCD"
        
        SOLUTION (3-step matching):
            1. EXACT MATCH — code already sahi hai? (SCD == SCD ✅)
            2. REVERSE MAP — full name se code nikalo (SUPPLY CEILING DIFFUSER → SCD)
            3. FUZZY MATCH — closest match dhundho (Supply Diffuser ≈ SCD)
        
        Parameters:
            response: dict — The parsed AI response
        
        Returns:
            dict: Response with normalized symbol codes
        """
        
        symbols = response.get("symbols", [])
        normalized_symbols = []
        
        for symbol in symbols:
            code = symbol.get("code", "").strip().upper()
            description = symbol.get("description", "").strip().upper()
            
            # ------------------------------------------------------------------
            # Filter 1: Non-countable labels hatao
            # ------------------------------------------------------------------
            # T/A, T/B, F/A, F/B, LPS, N.C — yeh equipment nahi hain
            if code in self.non_countable:
                self.validation_stats["symbols_removed_non_countable"] += 1
                logging.info(f"Removed non-countable label: {code}")
                continue
            
            # ------------------------------------------------------------------
            # Match Strategy 1: EXACT CODE MATCH
            # ------------------------------------------------------------------
            # Agar AI ne sahi code diya hai (SCD, VD, FCU, etc.)
            if code in self.valid_codes:
                # Code sahi hai — description bhi fix karo (consistency ke liye)
                symbol["code"] = code
                symbol["description"] = self.legend_map[code]
                normalized_symbols.append(symbol)
                continue
            
            # ------------------------------------------------------------------
            # Match Strategy 2: REVERSE MAP (full name se code)
            # ------------------------------------------------------------------
            # AI ne code nahi diya, but full name diya hai
            # "SUPPLY CEILING DIFFUSER" → "SCD"
            if description in self.reverse_map:
                matched_code = self.reverse_map[description]
                
                self.validation_stats["symbols_normalized"] += 1
                self.validation_stats["fuzzy_matches"].append({
                    "original_code": symbol.get("code", ""),
                    "original_desc": symbol.get("description", ""),
                    "matched_code": matched_code,
                    "match_type": "reverse_map",
                })
                
                symbol["code"] = matched_code
                symbol["description"] = self.legend_map[matched_code]
                normalized_symbols.append(symbol)
                logging.info(f"Normalized via reverse map: '{code}' → '{matched_code}'")
                continue
            
            # ------------------------------------------------------------------
            # Match Strategy 3: FUZZY MATCHING (approximate match)
            # ------------------------------------------------------------------
            # AI ne kuch aisa diya jo exactly match nahi karta
            # "Supply Diffuser" ko "SUPPLY CEILING DIFFUSER" se match karo
            best_match = self._fuzzy_match(code, description)
            
            if best_match:
                matched_code, similarity = best_match
                
                self.validation_stats["symbols_normalized"] += 1
                self.validation_stats["fuzzy_matches"].append({
                    "original_code": symbol.get("code", ""),
                    "original_desc": symbol.get("description", ""),
                    "matched_code": matched_code,
                    "match_type": "fuzzy",
                    "similarity": similarity,
                })
                
                symbol["code"] = matched_code
                symbol["description"] = self.legend_map[matched_code]
                
                # Fuzzy match pe confidence kam karo (100% sure nahi hain)
                if similarity < 0.8:
                    symbol["confidence"] = "medium"
                
                normalized_symbols.append(symbol)
                logging.info(
                    f"Fuzzy matched: '{code}/{description}' → "
                    f"'{matched_code}' (similarity: {similarity:.2f})"
                )
                continue
            
            # ------------------------------------------------------------------
            # NO MATCH FOUND — Unrecognized symbol
            # ------------------------------------------------------------------
            self.validation_stats["unrecognized_symbols"].append({
                "code": symbol.get("code", ""),
                "description": symbol.get("description", ""),
                "tile_id": response.get("tile_id", "unknown"),
            })
            
            logging.warning(
                f"Unrecognized symbol: code='{code}', "
                f"desc='{description}' in tile {response.get('tile_id')}"
            )
            
            # Include but mark for review
            symbol["confidence"] = "low"
            normalized_symbols.append(symbol)
        
        response["symbols"] = normalized_symbols
        return response
    
    def flag_low_confidence(self, response):
        """
        Symbols ko confidence level ke hisab se separate karo.
        
        CATEGORIES:
            HIGH   → Count directly — reliable results
            MEDIUM → Include but flag — manual check recommended
            LOW    → Exclude from final count — needs human review
        
        Parameters:
            response: dict — Normalized AI response
        
        Returns:
            dict: Response with added confidence_summary section
        
        ADDED FIELDS:
            response["confidence_summary"] = {
                "high_confidence": [...],
                "medium_confidence": [...],
                "low_confidence": [...],
                "excluded_count": 0,
            }
        """
        
        symbols = response.get("symbols", [])
        
        high_conf = []     # Bharose wale — seedha count karo
        medium_conf = []   # Theek hain — check karo ek baar
        low_conf = []      # Shak hai — human dekhega
        
        for symbol in symbols:
            confidence = symbol.get("confidence", "medium").lower()
            
            if confidence == "high":
                high_conf.append(symbol)
            elif confidence == "medium":
                medium_conf.append(symbol)
            else:
                low_conf.append(symbol)
                self.validation_stats["low_confidence_flagged"] += 1
        
        # ------------------------------------------------------------------
        # Confidence summary add karo
        # ------------------------------------------------------------------
        response["confidence_summary"] = {
            "high_confidence_count": sum(s["quantity"] for s in high_conf),
            "medium_confidence_count": sum(s["quantity"] for s in medium_conf),
            "low_confidence_count": sum(s["quantity"] for s in low_conf),
            "total_reliable": sum(s["quantity"] for s in high_conf + medium_conf),
            "excluded_for_review": sum(s["quantity"] for s in low_conf),
        }
        
        # Agar koi bhi LOW hai toh human review flag set karo
        if low_conf:
            response["requires_human_review"] = True
        
        return response
    
    def process_response(self, raw_response):
        """
        COMPLETE processing pipeline — validate → normalize → confidence filter.
        
        Yeh ek convenience function hai — teeno steps ek call mein.
        
        Parameters:
            raw_response: dict — Raw parsed JSON from Gemini
        
        Returns:
            tuple: (processed_response, is_valid, errors, warnings)
        """
        
        # Step 1: Validate
        is_valid, errors, warnings = self.validate_response(raw_response)
        
        if not is_valid:
            return raw_response, False, errors, warnings
        
        # Step 2: Normalize symbol names
        normalized = self.normalize_symbol_names(raw_response)
        
        # Step 3: Confidence filtering
        processed = self.flag_low_confidence(normalized)
        
        return processed, True, errors, warnings
    
    def generate_validation_report(self, output_dir=None):
        """
        Validation statistics ka report JSON mein save karo.
        
        Output: data/ai_results/_validation_report.json
        
        ISME KYA HOTA HAI:
            - Kitne responses validate hue
            - Kitne valid the, kitne invalid
            - Kitne symbols normalize hue (fuzzy matches ki detail)
            - Kitne unrecognized symbols the
            - Kitne low confidence flags lage
        """
        
        if output_dir is None:
            output_dir = CONFIG["AI_RESULTS_DIR"]
        
        os.makedirs(output_dir, exist_ok=True)
        
        report = {
            "report_name": "Response Validation Report",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": self.validation_stats,
            "validation_rate": (
                f"{self.validation_stats['valid_responses']}/"
                f"{self.validation_stats['total_responses_validated']}"
            ),
        }
        
        report_path = os.path.join(output_dir, "_validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n  📝 Validation report saved: _validation_report.json")
        logging.info(f"Validation report saved: {report_path}")
        
        return report
    
    # ======================================================================
    # PRIVATE METHODS
    # ======================================================================
    
    def _load_legend_map(self):
        """Legend map JSON load karo."""
        map_path = CONFIG["LEGEND_MAP_PATH"]
        
        if not os.path.exists(map_path):
            raise FileNotFoundError(f"Legend map not found: {map_path}")
        
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _fuzzy_match(self, code, description, threshold=0.6):
        """
        Fuzzy matching — approximate string comparison.
        
        HOW IT WORKS:
            SequenceMatcher do strings ki "similarity ratio" calculate karta hai.
            0.0 = bilkul different
            1.0 = identical
            0.6+ = good enough match (humara threshold)
        
        EXAMPLE:
            "Supply Diffuser" vs "SUPPLY CEILING DIFFUSER" = 0.72 ✅
            "Random Text"     vs "SUPPLY CEILING DIFFUSER" = 0.15 ❌
        
        Parameters:
            code: AI ka code (e.g., "SCD" ya kuch aur)
            description: AI ki description (e.g., "Supply Diffuser")
            threshold: Minimum similarity score (default 0.6 = 60%)
        
        Returns:
            tuple: (matched_code, similarity_score) ya None agar match nahi
        """
        
        best_code = None
        best_score = 0
        
        # AI ke input ko ek search string banao
        search_text = f"{code} {description}".upper()
        
        # Har legend entry se compare karo
        for legend_code, legend_name in self.legend_map.items():
            
            # Skip non-countable labels
            if legend_code in self.non_countable:
                continue
            
            # Code-to-code comparison
            # "SCD" vs "SCD" = direct match (fast path)
            code_similarity = SequenceMatcher(
                None, code.upper(), legend_code.upper()
            ).ratio()
            
            # Description-to-description comparison
            # "Supply Diffuser" vs "SUPPLY CEILING DIFFUSER"
            desc_similarity = SequenceMatcher(
                None, search_text, f"{legend_code} {legend_name}".upper()
            ).ratio()
            
            # Best score lo (code ya description, jo zyada match ho)
            score = max(code_similarity, desc_similarity)
            
            if score > best_score:
                best_score = score
                best_code = legend_code
        
        # Threshold check — kya best match kaafi acha hai?
        if best_score >= threshold and best_code:
            return (best_code, round(best_score, 3))
        
        return None


# ============================================================================
# MAIN EXECUTION — Standalone Test
# ============================================================================
if __name__ == "__main__":
    
    print("=" * 60)
    print("  🚀 DAY 11: RESPONSE PARSER TEST")
    print("=" * 60)
    
    parser = ResponseParser()
    
    # ------------------------------------------------------------------
    # Test 1: Valid Response
    # ------------------------------------------------------------------
    print("\n  📋 Test 1: Valid response with normalization needed...")
    
    test_response = {
        "tile_id": "tile_y2700_x3600.png",
        "tile_coordinates": {
            "y_start": 2700, "x_start": 3600,
            "y_end": 3900, "x_end": 4800
        },
        "symbols": [
            {
                "code": "SCD",
                "description": "SUPPLY CEILING DIFFUSER",
                "quantity": 2,
                "confidence": "high",
                "instances": [
                    {"size": "600x600", "flow_rate_lps": 250, "tag": None,
                     "room": "OFFICE", "position": "center", "overlap_risk": False},
                    {"size": "450x450", "flow_rate_lps": 180, "tag": None,
                     "room": None, "position": "edge", "overlap_risk": True}
                ]
            },
            {
                # AI ne galat name diya — "Supply Diffuser" instead of "SCD"
                "code": "Supply Diffuser",
                "description": "Ceiling type supply diffuser",
                "quantity": 1,
                "confidence": "medium",
                "instances": [
                    {"size": "300x300", "flow_rate_lps": 120, "tag": None,
                     "room": None, "position": "center", "overlap_risk": False}
                ]
            },
            {
                # Non-countable label — should be removed
                "code": "T/A",
                "description": "TO ABOVE",
                "quantity": 1,
                "confidence": "high",
                "instances": [
                    {"size": None, "flow_rate_lps": None, "tag": None,
                     "room": None, "position": "center", "overlap_risk": False}
                ]
            },
            {
                "code": "VD",
                "description": "VOLUME DAMPER",
                "quantity": 1,
                "confidence": "low",
                "instances": [
                    {"size": "300x200", "flow_rate_lps": None, "tag": None,
                     "room": None, "position": "center", "overlap_risk": False}
                ]
            },
        ],
        "duct_runs_detected": [],
        "tile_quality": {
            "overall_clarity": "high",
            "clutter_level": "medium",
            "text_readability": "clear",
            "symbol_density": "normal"
        },
        "warnings": [],
        "requires_human_review": False
    }
    
    # Process
    processed, is_valid, errors, warnings = parser.process_response(test_response)
    
    print(f"     Valid: {is_valid}")
    print(f"     Errors: {errors}")
    print(f"     Warnings: {warnings}")
    print(f"     Symbols after processing: {len(processed['symbols'])}")
    
    for s in processed["symbols"]:
        print(f"       → {s['code']:6s} | {s['description']:30s} | "
              f"qty={s['quantity']} | conf={s['confidence']}")
    
    if "confidence_summary" in processed:
        print(f"\n     Confidence Summary:")
        for k, v in processed["confidence_summary"].items():
            print(f"       {k:25s}: {v}")
    
    # ------------------------------------------------------------------
    # Test 2: Process actual AI results (if they exist)
    # ------------------------------------------------------------------
    results_dir = CONFIG["AI_RESULTS_DIR"]
    
    if os.path.exists(results_dir):
        result_files = [f for f in os.listdir(results_dir) 
                       if f.endswith("_result.json") and not f.startswith("_")]
        
        if result_files:
            print(f"\n  📋 Test 2: Processing {len(result_files)} actual AI results...")
            
            for rf in result_files:
                filepath = os.path.join(results_dir, rf)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                processed, is_valid, errors, warnings = parser.process_response(data)
                status = "✅" if is_valid else "❌"
                symbols_count = len(processed.get("symbols", []))
                print(f"     {status} {rf}: {symbols_count} symbols")
                
                # Save processed version
                processed_path = filepath  # Overwrite with normalized version
                with open(processed_path, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
    
    # ------------------------------------------------------------------
    # Generate Report
    # ------------------------------------------------------------------
    report = parser.generate_validation_report()
    
    print(f"\n  📊 Validation Stats:")
    stats = parser.validation_stats
    print(f"     Validated     : {stats['total_responses_validated']}")
    print(f"     Valid         : {stats['valid_responses']}")
    print(f"     Invalid       : {stats['invalid_responses']}")
    print(f"     Normalized    : {stats['symbols_normalized']}")
    print(f"     Non-countable : {stats['symbols_removed_non_countable']}")
    print(f"     Low conf      : {stats['low_confidence_flagged']}")
    print(f"     Unrecognized  : {len(stats['unrecognized_symbols'])}")
    
    if stats['fuzzy_matches']:
        print(f"\n  🔄 Fuzzy Matches:")
        for fm in stats['fuzzy_matches']:
            print(f"     '{fm['original_code']}' → '{fm['matched_code']}' "
                  f"({fm['match_type']}, sim={fm.get('similarity', 'N/A')})")
    
    print(f"\n  🎉 DAY 11 COMPLETE!")
    print("=" * 60)
