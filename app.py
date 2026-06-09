from flask import Flask, request, jsonify, send_file
import os
import json
import time

app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    # ---------------------------------------------------------
    # PHASE 4: CONNECTING TO CORE ENGINE
    # ---------------------------------------------------------
    # In a full run, we would save the file and call:
    # os.system('python phase2_brain_engine.py')
    # os.system('python phase3_excel_exporter.py')
    # 
    # For this real-time demo, we simulate processing time 
    # and read the already computed Phase 3 data for speed.
    # ---------------------------------------------------------
    time.sleep(8) 
    
    merged_path = r'data\ai_results\_merged_counts.json'
    
    try:
        with open(merged_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        grand_total_items = data.get('grand_total_items', 0)
        
        # Calculate amount from our mockup Python logic
        market_rates = {
            "SCD": 6500, "RCD": 6500, "VD": 2500, "VAV": 45000, 
            "EDV": 1800, "EDH": 35000, "FSD": 8500, "DG": 4500,
            "BMO": 2000, "SLD": 8000, "CO2": 15000, "TD": 4000,
            "RR": 3500, "RLD": 8000, "BDD": 3000
        }
        
        flat_counts = data.get('flat_counts', {})
        total_pkr = 0
        for name, qty in flat_counts.items():
            code = name.split()[0]
            rate = market_rates.get(code, 5000)
            total_pkr += (qty * rate)

        return jsonify({
            "success": True, 
            "stats": {
                "total_items": grand_total_items,
                "grand_total": total_pkr
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download_boq', methods=['GET'])
def download():
    # Direct path to the generated Excel file from Phase 3
    excel_path = os.path.abspath('Phase3_Final_BOQ_Report.xlsx')
    return send_file(excel_path, as_attachment=True)

if __name__ == '__main__':
    print("=" * 60)
    print(" 🚀 Phase 4: Starting Web System Server on PORT 5000")
    print("=" * 60)
    app.run(port=5000, debug=False)
