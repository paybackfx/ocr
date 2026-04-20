# Insurance Document OCR - Moroccan Documents (OpenRouter) - Deployment

This folder isolates the `Insurance Document OCR - Moroccan Documents (OpenRouter)` workflow. Let's keep things clean!

## 🚀 How to Launch
Run the following command inside this directory:
```bash
docker compose up -d --build
```

## 🛠 Ports Assignment
- **n8n UI/Webhook:** `http://localhost:5678`
- **FastAPI/OpenCV Backend:** `http://localhost:8000` (Internal API uses `8000` via Docker network)

## 🔑 First-Time Setup
1. Go to `http://localhost:5678` to create your admin account.
2. Navigate to **Workflows -> Import from File**.
3. Import the `workflow.json` located inside `init-workflows/`.
4. Update any credentials (if needed) and ensure HTTP Request nodes point to `http://openrouter-workflow-opencv:8000` instead of `localhost` or public IP, so it connects via the Docker network.
5. Activate the workflow!

## 🧪 Testing
```bash
curl -v -X POST "http://localhost:5678/webhook/insurance-ocr-openrouter"  -F "data=@/path/to/your/image.jpeg"
```

## 🛑 Stopping
```bash
docker compose down
```
