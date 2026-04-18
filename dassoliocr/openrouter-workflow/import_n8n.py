import json, urllib.request

# 1. Lire le fichier
with open('/home/sirfennoune/dassoliocr/openrouter-workflow/init-workflows/workflow.json', 'r') as f:
    wf = json.load(f)[0] # Prend le premier workflow du tableau

# 2. Préparer les données pour n8n
data = json.dumps({
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf["settings"],
    "active": True
}).encode('utf-8')

# 3. L'envoyer de force à n8n !
req = urllib.request.Request("http://localhost:5678/rest/workflows", data=data, headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print("✅ REUSSITE ! Le workflow a été importé dans n8n !")
except Exception as e:
    print(f"❌ Échec: {e}")
