# 🌍 Federated Data System for a Chaptered NGO

A production-style data engineering project simulating a **federated data architecture** 
for a multi-chapter NGO operating across Kenya.

Built by **Kevin Mbugua** · [@mbuguakevvz](https://github.com/mbuguakevvz)

---

## 📌 Problem Statement

Large NGOs operate across multiple regions, each chapter collecting its own beneficiary, 
project, and funding data in isolation. This makes cross-chapter reporting slow, 
inconsistent, and donor-unfriendly.

This system solves that by federating data across all chapters into a unified 
analytical layer — without centralizing raw data storage.

---

## 🏗️ Architecture

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Chapter Data Nodes | DuckDB (per-chapter files) |
| Federation API | FastAPI + Uvicorn |
| ETL Pipelines | Python (Airflow-style DAGs) |
| Central Warehouse | DuckDB (Star Schema) |
| Dashboard | FastAPI + Plotly |
| Language | Python 3.x |
| Version Control | Git + GitHub |

---

## 📂 Project Structure

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/mbuguakevvz/federated-ngo-system.git
cd federated-ngo-system
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
source venv/bin/activate          # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed the chapter databases
```bash
python scripts/seed_chapters.py
```

### 5. Run the ETL pipeline
```bash
python etl_pipelines/etl_to_warehouse.py
```

### 6. Start the Federation API
```bash
uvicorn federation_api.main:app --reload
# Visit http://127.0.0.1:8000/docs
```

### 7. Start the Dashboard
```bash
uvicorn dashboard.app:app --reload --port 8080
# Visit http://127.0.0.1:8080
```

---

## 📊 What the Dashboard Shows

- **600 beneficiaries** across 3 chapters
- **12 projects** spanning Health, Education, WASH, Agriculture, Livelihoods & Protection
- **1,500 service delivery records**
- **KES 16.9M** in funding from donors including USAID, UKAID, Gates Foundation & UNICEF
- Interactive charts: services by type, funding by donor, beneficiaries by gender/chapter, age groups, project themes, and time-series trends

---

## 🌐 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | System info |
| `GET /health` | Chapter node health check |
| `GET /kpi` | Cross-chapter KPI summary |
| `GET /beneficiaries` | All beneficiaries (filterable) |
| `GET /beneficiaries/count` | Count by chapter/gender/county |
| `GET /projects` | All projects (filterable) |
| `GET /projects/summary` | Budget & status breakdown |
| `GET /funds` | All funding records |
| `GET /funds/by-donor` | Aggregated donor report |
| `GET /services` | Service delivery records |
| `GET /services/summary` | Services by type |

---

## 💡 Key Data Engineering Concepts Demonstrated

- **Data Federation** — querying distributed nodes without centralizing raw data
- **Star Schema Design** — dimensional modeling for analytical queries
- **ETL Pipeline** — extract, transform, load with audit logging
- **REST API Design** — FastAPI with filtering, fan-out, and result merging
- **Realistic Seed Data** — Kenyan NGO context with real donor names, counties, and thematic areas
- **Data Warehousing** — DuckDB as a modern OLAP engine

---

## 👤 Author

**Kevin Mbugua**
Data Engineer · Nyeri, Kenya
GitHub: [@mbuguakevvz](https://github.com/mbuguakevvz)

