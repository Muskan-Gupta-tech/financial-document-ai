# FinEdge AI &bull; Financial Document Intelligence &amp; Validation Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20(ONNX)-orange.svg)]()
[![Tests Passing](https://img.shields.io/badge/tests-18%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FinEdge AI** is a production-grade Financial Document Intelligence microservice and web studio built to ingest, validate, extract, and reconcile financial documents (Invoices, Balance Sheets, Profit & Loss Statements, and Cash Flow Statements) across native and scanned PDFs, JPGs, and PNGs.

---

## 1. Key Features

- **7-Stage Processing Pipeline**: File integrity validation &rarr; High-DPI rasterization (PyMuPDF 200 DPI) &rarr; Fast CPU ONNX OCR (RapidOCR) &rarr; Dual AI Extraction Engine (Gemini 2.5 Flash + Deterministic Spatial Fallback) &rarr; Accounting Tolerance & Formula Math Engine &rarr; Evidence Grounding &rarr; SQLAlchemy Persistence.
- **Audited Financial Instruments**:
  - **Invoices**: Unit price &times; quantity verification, line total net sums, tax & discount footing, total cash paid vs balance due.
  - **Balance Sheets**: Multi-period balance equation (`Total Capital & Liabilities = Total Assets`), schedule aggregation.
  - **Profit & Loss**: Operating revenues &minus; expenses = Net Profit Before Tax, earnings per share, group appropriations.
  - **Cash Flow Statements**: Operating + Investing + Financing + Foreign Exchange delta cross-footing; Opening cash + Net change = Closing cash.
- **Executive Fintech Dashboard**:
  - Modern dark/light glassmorphic UI with live KPI metrics (Repository count, Reconciliation pass rate, Category coverage, Confidence score).
  - Drag-and-drop document upload with automatic file metadata inspection.
  - 1-Click sample document loader for rapid evaluation.
  - Category filter pills, real-time search, and interactive audit matrix.
  - Raw JSON viewer with one-click clipboard copy.
  - **Zero Node.js/npm dependencies**: Pure semantic HTML5, CSS3, and ES6 JavaScript running directly out of FastAPI.

---

## 2. System Architecture

```
User / API Client
       │ (PDF / PNG / JPG)
       ▼
1. Document Validation Layer
   ├── MIME Type Verification (Magic bytes)
   ├── Corruption & Payload Integrity Check
   └── Maximum 3 Pages Constraint
       │
       ▼
2. OCR & Rasterization Engine
   ├── Native Text Extraction (PyMuPDF)
   └── High-DPI Scanned Rasterization (200 DPI) + RapidOCR (ONNX Runtime)
       │
       ▼
3. Dual AI Extraction Engine
   ├── Primary: Cloud LLM (Gemini 2.5 Flash Structured Outputs)
   └── Fallback: Deterministic Spatial/Regex Domain Extractor (100% Offline Uptime)
       │
       ▼
4. Financial Calculation & Validation Engine
   ├── Strict Accounting Formulas
   └── Numerical Tolerance Evaluation (0.05 / 1.0 for rounded crores)
       │
       ▼
5. Evidence Grounding & Confidence
   └── Bounding box/snippet attribution, page citations, token confidence
       │
       ▼
6. Storage & REST API
   ├── SQLite / PostgreSQL persistence (SQLAlchemy 2.0)
   └── Interactive Web Studio & OpenAPI 3.0 Documentation (/docs)
```

![System Architecture](docs/architecture.png)

### Documentation & Deliverables
- **Solution Presentation (16 Slides PDF)**: [`docs/solution_presentation.pdf`](docs/solution_presentation.pdf)
- **High-Resolution Architecture Diagram**: [`docs/architecture.png`](docs/architecture.png)

---

## 3. Quick Start Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12
- `pip` package manager

### Step 1: Set Up Virtual Environment

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

*(Optional)* If you wish to use Google Gemini for AI extraction, set your API key in `.env`:
```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```
> **Note:** FinEdge AI includes an autonomous high-precision fallback extractor, so it works completely offline without an API key!

### Step 3: Run the Application

**Option A: 1-Click Batch File (Windows)**
Double click `run.bat` or run:
```cmd
run.bat
```

**Option B: Python Launcher (All Platforms)**
```bash
python run.py
```

Open your browser to:
- **Web Studio Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 4. Running Automated Tests

Run the full test suite with `pytest`:
```bash
pytest backend/tests -v
```

All 18 unit and integration tests will execute:
- File validation constraints (MIME checks, >3 pages rejection)
- Extraction accuracy across Invoices, Balance Sheets, P&L, and Cash Flow statements
- Strict financial calculation and tolerance checks
- REST API endpoint contracts and JSON schema responses

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/process` | Ingest and process a financial document (`multipart/form-data`) |
| `GET` | `/api/v1/documents` | List all processed documents with status summaries |
| `GET` | `/api/v1/documents/{name}` | Retrieve complete structured JSON extraction & validations |
| `GET` | `/api/v1/health` | Service health status and OCR engine readiness |
| `GET` | `/docs` | Interactive OpenAPI / Swagger UI |

---

## 6. Directory Structure

```
financial-document-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Document & health endpoints
│   │   ├── core/              # Config, DB engine, logging
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # OCR, AI extraction, validation engine
│   │   └── main.py            # FastAPI entrypoint & router mounts
│   ├── requirements.txt       # Backend dependencies
│   └── tests/                 # 18 pytest test cases
├── data/
│   ├── sample_documents/      # 4 evaluator test documents
│   └── uploads/               # Processed documents storage
├── frontend/
│   ├── static/
│   │   ├── css/finedge.css    # Executive fintech dark/light design system
│   │   └── js/                # Dashboard & result inspector controllers
│   └── templates/             # Jinja2 HTML templates
├── Dockerfile                 # Containerized deployment config
├── README.md                  # System documentation
├── requirements.txt           # Root requirements pointer
├── run.bat                    # Windows 1-click launcher
└── run.py                     # Cross-platform runner script
```

---

## 7. License

MIT License. Free for educational and commercial use.
