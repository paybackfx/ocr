# OnWave — Automated Document Processing & Accounting Reconciliation

**SaaS Platform for Moroccan Fiduciaries** — Powered by YOLO + OpenCV + Gemini Vision + n8n

## 🚀 How to Launch
```bash
docker compose up -d --build
```

## 🛠 Services & Ports
| Service | Port | Description |
|---------|------|-------------|
| **n8n** (Workflow Engine) | `http://localhost:5678` | OCR orchestration + OpenRouter AI |
| **FastAPI/OpenCV** | `http://localhost:8000` | YOLO A4 detection + Image optimization + **Reconciliation Engine** |
| **React GUI** | `http://localhost:5173` | Frontend interface |

## 🔑 First-Time Setup
1. Navigate to `http://localhost:5678` and create your n8n admin account.
2. The workflow is auto-imported from `init-workflows/workflow.json`.
3. Set your OpenRouter API credentials inside n8n.
4. Activate the workflow.

## 📊 Reconciliation Engine API
The FastAPI backend includes a dedicated accounting endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "invoices": [
      {"Date": "2026-01-15", "Fournisseur": "ONEE", "Montant_HT": 1000, "Montant_TVA": 200, "Montant_TTC": 1200}
    ],
    "bank_statements": [
      {"Date": "2026-01-20", "Libelle": "VIR ONEE FACTURE", "Debit": 1200, "Credit": 0}
    ]
  }'
```

### What it does:
1. **Matches** invoices to bank transactions (amount + date constraint)
2. **Generates PCGM journal entries** (Écritures Comptables) with correct account codes
3. **Flags** unmatched items for human review

### PCGM Accounts Used:
| Code | Label |
|------|-------|
| 6111 | Achats de marchandises (default) |
| 61251 | Achats d'électricité |
| 6145 | Frais postaux et télécommunications |
| 61241 | Achats de combustibles |
| 6134 | Primes d'assurance |
| 34552 | TVA récupérable sur charges |
| 4411 | Fournisseurs |
| 5141 | Banques |

## 🛑 Stopping
```bash
docker compose down
```
