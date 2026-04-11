import os
import json
import logging
import pandas as pd
from datetime import datetime
from config import CONFIG

# ============================================================================
# phase3_excel_exporter.py — Phase 3: Human Review UI & BOQ Generation
# ============================================================================
#
# 🎯 OBJECTIVE:
# AI ne jo count kiya hai usko ek Professional Excel Sheet mein convert karna.
# Is sheet mein ek "Human Review UI" hoga taake Engineer (USER) khud:
#   1. AI ki quantity verify kare.
#   2. Agar AI ne miss kiya hai toh manually correct kare.
#   3. Market rates multiply karke final Amount nikaale.
#
# TAB 1: BOQ Summary
# TAB 2: Detailed Quantity (with Human Verification)
# ============================================================================

# Dummy/Reference Market rates (PKR ya USD) - in this case PKR estimates
MARKET_RATES = {
    "SCD": 6500,
    "RCD": 6500,
    "VD": 2500,
    "VAV": 45000,
    "EDV": 1800,
    "EDH": 35000,
    "FSD": 8500,
    "DG": 4500,
    "BMO": 2000,
    "SLD": 8000,
    "CO2": 15000,
    "TD": 4000,
    "RR": 3500,
    "RLD": 8000,
    "BDD": 3000
}

def generate_excel_boq():
    print("=" * 60)
    print("  🏗️  PHASE 3: EXCEL BOQ GENERATOR (With Human Review UI)")
    print("=" * 60)

    # 1. Load Merged Counts
    results_dir = CONFIG["AI_RESULTS_DIR"]
    merged_path = os.path.join(results_dir, "_merged_counts.json")
    
    if not os.path.exists(merged_path):
        print(f"❌ _merged_counts.json not found at {merged_path}")
        print("   Please run Phase 2 successfully first.")
        return

    with open(merged_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Extract Data for DataFrame
    boq_by_cat = data.get("boq_by_category", {})
    size_info = data.get("size_details", {})
    
    rows = []
    
    for category, items in boq_by_cat.items():
        for full_name, qty in items.items():
            # 'SCD (SUPPLY CEILING DIFFUSER)' -> code='SCD', desc='SUPPLY CEILING DIFFUSER'
            parts = full_name.split(" ", 1)
            code = parts[0]
            desc = parts[1].replace("(", "").replace(")", "") if len(parts) > 1 else full_name
            
            # Common size if AI detected it
            common_size = "Varied"
            if full_name in size_info and "most_common" in size_info[full_name]:
                common_size = size_info[full_name]["most_common"]

            unit_rate = MARKET_RATES.get(code, 5000) # Default 5000 if not in dictionary

            rows.append({
                "Category": category.upper(),
                "Code": code,
                "Description": desc,
                "Size / Spec": common_size,
                "Unit": "No.",
                "AI Extracted Qty": qty,
                "Verification": "Needs Review", # Dropdown default
                "Revised Qty": "",             # Blank for human input
                "Final Qty": "",               # Formula will be added
                "Unit Rate (PKR)": unit_rate,
                "Total Amount": ""             # Formula will be added
            })

    df = pd.DataFrame(rows)
    
    # Sort for better reading
    df = df.sort_values(by=["Category", "Code"])

    # 3. Create Excel File with Formatting
    out_dir = os.path.dirname(CONFIG["TILE_MAP_PATH"]) # Base project dir or output folder
    excel_path = os.path.join(out_dir, "Phase3_Final_BOQ_Report.xlsx")
    
    writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
    
    # -------------------------------------------------------------
    # TAB 1: Human Review & Detailed BOQ
    # -------------------------------------------------------------
    df.to_excel(writer, sheet_name="Human Review BOQ", index=False)
    workbook = writer.book
    worksheet = writer.sheets["Human Review BOQ"]

    # Formats
    header_format = workbook.add_format({
        'bold': True, 'text_wrap': True, 'valign': 'center', 'align': 'center',
        'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1
    })
    
    ai_col_format = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1, 'align': 'center'})
    human_col_format = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1, 'align': 'center'})
    money_format = workbook.add_format({'num_format': '#,##0', 'border': 1})
    border_format = workbook.add_format({'border': 1, 'valign': 'center'})
    
    # Set Columns Width
    worksheet.set_column('A:A', 18, border_format)   # Category
    worksheet.set_column('B:B', 10, border_format)   # Code
    worksheet.set_column('C:C', 35, border_format)   # Description
    worksheet.set_column('D:D', 15, border_format)   # Size
    worksheet.set_column('E:E', 8, border_format)   # Unit
    worksheet.set_column('F:F', 16, ai_col_format)   # AI Qty
    worksheet.set_column('G:G', 16, human_col_format)# Verification Status
    worksheet.set_column('H:H', 15, human_col_format)# Revised Qty
    worksheet.set_column('I:I', 12, ai_col_format)   # Final Qty
    worksheet.set_column('J:J', 15, money_format)    # Unit Rate
    worksheet.set_column('K:K', 18, money_format)    # Total Amount

    # Write Headers with Format
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)

    # Freeze Panes
    worksheet.freeze_panes(1, 4)

    # 4. Add Excel Logic (Data Validation & Formulas)
    for row_num in range(1, len(df) + 1):
        qty = df.iloc[row_num-1]["AI Extracted Qty"]
        unit_rate = df.iloc[row_num-1]["Unit Rate (PKR)"]
        total_val = qty * unit_rate

        # Dropdown for Verification Col G
        worksheet.data_validation(f'G{row_num+1}', {
            'validate': 'list',
            'source': ['Needs Review', 'Approved - Qty OK', 'Corrected Manually']
        })
        
        # Formula for Final Qty (Col I)
        # IF G="Corrected Manually", then H, else F
        worksheet.write_formula(
            row_num, 8, 
            f'=IF(G{row_num+1}="Corrected Manually", IF(H{row_num+1}="", F{row_num+1}, H{row_num+1}), F{row_num+1})', 
            ai_col_format,
            value=qty
        )
        
        # Formula for Total Amount (Col K) = Final Qty (I) * Unit Rate (J)
        worksheet.write_formula(
            row_num, 10,
            f'=I{row_num+1}*J{row_num+1}',
            money_format,
            value=total_val
        )

    # Add a Grand Total row
    last_row = len(df) + 1
    grand_total = (df["AI Extracted Qty"] * df["Unit Rate (PKR)"]).sum()
    worksheet.write(last_row, 9, "GRAND TOTAL", header_format)
    worksheet.write_formula(last_row, 10, f"=SUM(K2:K{last_row})", workbook.add_format({'bold': True, 'num_format': '#,##0', 'bg_color': '#E2EFDA', 'border': 1}), value=grand_total)


    # -------------------------------------------------------------
    # TAB 2: Per-Tile Details (Verification Helper)
    # -------------------------------------------------------------
    tile_files = sorted([f for f in os.listdir(results_dir) if f.endswith("_result.json") and not f.startswith("_")])
    tile_rows = []
    
    for tf in tile_files:
        t_path = os.path.join(results_dir, tf)
        with open(t_path, 'r', encoding='utf-8') as f:
            t_data = json.load(f)
            
        tile_id = t_data.get("tile_id", tf)
        symbols = t_data.get("symbols", [])
        for sym in symbols:
            q = sym.get("quantity", 0)
            if q > 0:
                tile_rows.append({
                    "Tile Name": tile_id,
                    "Code": sym.get("code", ""),
                    "Description": sym.get("description", ""),
                    "Quantity Detected": q
                })
                
    if tile_rows:
        df_tiles = pd.DataFrame(tile_rows)
        df_tiles.to_excel(writer, sheet_name="Per-Tile Details", index=False)
        worksheet_tiles = writer.sheets["Per-Tile Details"]
        
        # Formatting for TAB 2
        worksheet_tiles.set_column('A:A', 25, border_format)
        worksheet_tiles.set_column('B:B', 15, border_format)
        worksheet_tiles.set_column('C:C', 35, border_format)
        worksheet_tiles.set_column('D:D', 18, border_format)
        
        for col_num, value in enumerate(df_tiles.columns.values):
            worksheet_tiles.write(0, col_num, value, header_format)
        
        worksheet_tiles.freeze_panes(1, 1)

    # -------------------------------------------------------------
    # Finalize
    # -------------------------------------------------------------
    writer.close()
    
    print(f"  ✅ SUCCESS: Excel BOQ UI Generated!")
    print(f"  📁 File Path: {excel_path}")
    print("\n  👉 INSTRUCTIONS FOR HUMAN REVIEW:")
    print("     1. Open the Excel file.")
    print("     2. Go to 'Verification' column (Yellow columns).")
    print("     3. Change status to 'Approved' or 'Corrected Manually'.")
    print("     4. If Corrected, enter your quantity in 'Revised Qty'.")
    print("     5. Final Quantities and Totals will update automatically!")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    generate_excel_boq()
