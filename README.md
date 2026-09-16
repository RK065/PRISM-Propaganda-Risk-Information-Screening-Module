# Content Propaganda & Paid Campaign Detector

A full-stack intelligence platform for analyzing social media posts, detecting propaganda vs. paid promotional campaigns, and verifying factual claims.

## 📁 Repository Structure

```
├── content-detector-system/    # Backend FastAPI engine, ML classification & fact-checking
│   ├── content_detector_api.py # Core REST API
│   ├── ml_classifier.py        # ML detection pipeline
│   ├── advanced_fact_checking.py # Fact verification
│   ├── Dockerfile              # Backend containerization
│   └── requirements.txt        # Python dependencies
│
├── content-detector-ui/        # Modern Next.js frontend application
│   ├── app/                    # Next.js app router (dashboard, analyzer, fact-check)
│   ├── lib/api.ts              # API client integration
│   └── package.json            # Node.js dependencies
│
└── detector-dashboard-demo.html# Interactive standalone HTML dashboard preview
```

## 🚀 Quick Start

### 1. Backend Setup (FastAPI)

```bash
cd content-detector-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python content_detector_api.py
```
The API server will run on `http://localhost:8000`.

### 2. Frontend Setup (Next.js)

```bash
cd content-detector-ui
npm install
npm run dev
```
The UI application will run on `http://localhost:3000`.

## 🛡️ License

MIT License
