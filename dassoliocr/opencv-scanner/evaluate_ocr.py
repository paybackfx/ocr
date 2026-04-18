import requests
import json
import sys

# Ground Truth Data from the provided Carte Grise image
TRUTH = {
    "nom_complet": "MOHAMED ABDOU DASSOULI",
    "matricule": "56532 - د - 6", # Accepting exact or variation of: 56532-د-6
    "marque": "LAND ROVER",
    "modele": "-", # Blank or DASH on the document
    "genre": "STATION WAGON",
    "energie": "Diesel",
    "numero_chassis": "SALLSAAF4AA227472", # Crucial: no O/I/Q
    "puissance_fiscale": "12",
    "cylindree_cc": "6", # "Nombre de cylindres" is 6
    "date_mise_circulation": "10/12/2010" # 1ere M.C.
}

def test_ocr(file_path):
    print(f"🚀 Sending {file_path} to n8n webhook...")
    
    url = "http://localhost:5678/webhook-test/insurance-ocr"
    try:
        with open(file_path, 'rb') as f:
            files = {'data': (file_path.split("/")[-1], f, 'image/jpeg' if file_path.endswith('jpeg') else 'application/pdf')}
            response = requests.post(url, files=files)
            
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
            
        data = response.json()
        carte_grise = data.get('carte_grise', {})
        
        print("\n📊 --- COMPARISON REPORT ---")
        score = 0
        total = len(TRUTH)
        
        for key, expected in TRUTH.items():
            actual = carte_grise.get(key, "NOT_FOUND")
            
            # Normalization for loose comparison (spaces, cases)
            exp_norm = str(expected).upper().replace(" ", "").replace("-", "")
            act_norm = str(actual).upper().replace(" ", "").replace("-", "")
            
            if exp_norm == act_norm:
                print(f"✅ {key.ljust(22)} : Extracted='{actual}' (Matches '{expected}')")
                score += 1
            else:
                print(f"❌ {key.ljust(22)} : Extracted='{actual}' | Expected='{expected}'")
                
        print(f"\n🎯 Accuracy: {score}/{total} ({(score/total)*100:.1f}%)")
        print("Raw JSON Data:")
        print(json.dumps(carte_grise, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"💥 Request Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evaluate_ocr.py <path_to_pdf_or_image>")
        sys.exit(1)
    
    test_ocr(sys.argv[1])
