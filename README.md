<div align="center">

# 🧠 OCR Platform — Moroccan Document Intelligence

### AI-powered document processing built for the Moroccan market

[![Made in Morocco](https://img.shields.io/badge/Made%20in-Morocco%20🇲🇦-red?style=flat-square)](https://github.com)
[![Stack](https://img.shields.io/badge/Stack-YOLO%20%7C%20FastAPI%20%7C%20n8n%20%7C%20React-blue?style=flat-square)](#tech-stack)
[![Contact](https://img.shields.io/badge/Contact-Get%20in%20touch-green?style=flat-square)](#contact)

</div>

---

## What is this?

This platform automates document processing workflows for **Moroccan fiduciaries and insurance companies** — turning scanned papers into structured, actionable data in seconds.

No more manual data entry. No more human errors. Just results.

---

## Products

### 📊 OnWave — Accounting Reconciliation
> *For fiduciaries, accountants, and financial offices*

Reads invoices and bank statements → automatically generates **PCGM-compliant journal entries**.

- Matches invoices to bank transactions by amount + date
- Generates ready-to-use accounting entries (PCGM Moroccan standard)
- Flags unmatched items for human review
- Processes Arabic, French, and mixed-language documents

### 🪪 AssuranceOCR — Insurance Document Processing
> *For insurance companies, brokers, and agencies*

Extracts structured data from Moroccan insurance documents with high accuracy.

- CIN, vehicle registration, contracts, attestations
- Handles handwritten + printed documents
- Returns clean JSON — plug directly into your existing system
- Multi-model AI for maximum accuracy

---

## How It Works

```
📄 Document Upload
        ↓
🔍 YOLO v8  →  Page detection & auto-crop
        ↓
🖼️  OpenCV  →  Image enhancement & optimization
        ↓
🤖  Gemini / OpenRouter AI  →  Text extraction & structuring
        ↓
⚙️  n8n  →  Workflow orchestration & business logic
        ↓
✅  Structured JSON output  →  Your system
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Document Detection | YOLOv8 (custom-trained on Moroccan documents) |
| Image Processing | OpenCV, Pillow |
| AI / Vision | Gemini Vision API, OpenRouter (multi-model) |
| Workflow Engine | n8n (self-hosted, full control) |
| Backend API | FastAPI — Python 3.10+ |
| Frontend | React 18 + Vite + TailwindCSS |
| Deployment | Docker Compose + Caddy (auto-HTTPS) |

---

## Key Features

- ✅ **Self-hosted** — your data never leaves your infrastructure
- ✅ **Moroccan-first** — trained and optimized for local documents
- ✅ **Bilingual** — handles Arabic and French natively
- ✅ **Modular** — easily plug into any existing system via REST API
- ✅ **Fast** — processes a full document in under 5 seconds
- ✅ **Accurate** — custom YOLO models trained specifically for A4 Moroccan docs

---

## Contact

Interested in integrating this into your workflow, or want a custom deployment?

🌐 **Website:** [fennoune.me](https://fennoune.me)
💼 **LinkedIn:** [Anas Fennoune](https://www.linkedin.com/in/anas-fennoune/)

> This is a **private repository** — source code is not publicly available.
> Get in touch to discuss licensing, integration, or custom development.

---

<div align="center">

**© 2025–2026 — All Rights Reserved**

*Built for Morocco 🇲🇦*

</div>
