# CloudIntelliGuard

**Explainable and Adaptive AI Framework for Proactive Cloud Security and User Behavior Intelligence**

Phase 1 — Backend and ML Foundation

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Quick Start (Docker)](#quick-start-docker)
6. [Quick Start (Local)](#quick-start-local)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [ML Pipeline](#ml-pipeline)
10. [Demo Dataset](#demo-dataset)
11. [Running Tests](#running-tests)
12. [Design Decisions and Limitations](#design-decisions-and-limitations)
13. [Roadmap](#roadmap)

---

## Overview

CloudIntelliGuard is a backend system for detecting anomalous cloud user
behaviour using dynamic temporal graph neural networks. It processes
CloudTrail-style event data, constructs per-user graph representations,
and applies configurable ML models to detect and explain anomalies.

**Key capabilities:**
- CloudTrail-style CSV/JSON ingestion
- Adaptive temporal window construction
- Dynamic user-action-service-resource directed graph
- Baseline GCN + Enhanced Temporal GNN anomaly detection
- Context-aware risk scoring (documented factor weights)
- Coordinated behaviour detection (heuristic, no attack labels invented)
- Rule-based explainability (GNNExplainer stub for Phase 2)
- Early-warning risk prediction (requires ≥3 historical points)
- Full REST API with JWT authentication

---

## Architecture

```
                            ┌─────────────────────┐
         CSV / JSON  ──────▶│   Data Ingestion     │
                            └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Preprocessing      │
                            │ (timestamp norm,     │
                            │  dedup, sort)        │
                            └──────────┬──────────┘
                                       │
                   ┌───────────────────▼───────────────────┐
                   │      Temporal Window Strategy          │
                   │  Fixed (24h default) | Adaptive        │
                   └───────────────────┬───────────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Graph Builder      │
                            │ user→action→service  │
                            │      →resource       │
                            └──────────┬──────────┘
                                       │
               ┌───────────────────────▼──────────────────────┐
               │               ML Detection                    │
               │  ┌─────────────────┐  ┌─────────────────┐   │
               │  │  Baseline GCN   │  │ Enhanced TGNN   │   │
               │  │ + Isolation     │  │ + Temporal Att. │   │
               │  │   Forest        │  │ + GAT (opt.)    │   │
               │  └────────┬────────┘  └────────┬────────┘   │
               └───────────┼───────────────────-─┼────────────┘
                           └─────────────────────┘
                                       │
               ┌────────────────────┬──┴──────────────┐
               │                    │                  │
    ┌──────────▼──────┐  ┌──────────▼──────┐ ┌────────▼──────┐
    │  Risk Scoring   │  │  Coordinated    │ │  Explainer    │
    │ (documented     │  │  Detection      │ │  (rule-based) │
    │  weights)       │  │  (heuristic)    │ └───────────────┘
    └──────────┬──────┘  └──────────┬──────┘
               │                    │
               └────────────────────┘
                           │
               ┌───────────▼───────────┐
               │  Incident + Alert +   │
               │  Recommendation Gen.  │
               └───────────┬───────────┘
                           │
               ┌───────────▼───────────┐
               │      REST API         │
               │    (FastAPI + JWT)    │
               └───────────────────────┘
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── security.py            # JWT + bcrypt
│   │   └── logging.py             # Structured JSON logging
│   ├── database/
│   │   ├── connection.py          # Async SQLAlchemy engine
│   │   └── seed.py                # Default roles + admin user
│   ├── models/
│   │   ├── database_models.py     # 14 SQLAlchemy ORM tables
│   │   ├── schemas.py             # Pydantic v2 API schemas
│   │   └── ml_models.py           # ML pipeline Pydantic schemas
│   ├── services/
│   │   ├── data_ingestion.py      # CSV/JSON ingestion
│   │   ├── preprocessing.py       # Normalization, dedup, sort
│   │   ├── feature_engineering.py # Raw + derived feature extraction
│   │   ├── graph_builder.py       # NetworkX temporal graph builder
│   │   ├── anomaly_service.py     # Detection orchestration
│   │   ├── risk_service.py        # Risk score persistence
│   │   ├── incident_service.py    # Incident + alert creation
│   │   ├── alert_service.py       # Alert acknowledgement
│   │   └── report_service.py      # DB-aggregated reports
│   ├── ml/
│   │   ├── temporal/
│   │   │   └── adaptive.py        # Fixed + adaptive window splitting
│   │   ├── baseline/
│   │   │   ├── model.py           # Baseline GCN
│   │   │   ├── detector.py        # Isolation Forest scorer
│   │   │   └── trainer.py         # Unsupervised training loop
│   │   ├── gnn/
│   │   │   └── model.py           # Enhanced Temporal GNN
│   │   ├── coordinated/
│   │   │   └── detector.py        # Coordinated behaviour heuristic
│   │   ├── risk/
│   │   │   └── scorer.py          # Documented context-aware scorer
│   │   ├── prediction/
│   │   │   └── predictor.py       # Early-warning linear predictor
│   │   ├── explainability/
│   │   │   └── explainer.py       # Rule-based explainer + GNNExplainer stub
│   │   └── evaluation/
│   │       ├── metrics.py         # sklearn metrics (GT only)
│   │       └── comparator.py      # Experiment comparator
│   └── api/
│       ├── auth.py                # POST /login, POST /register
│       ├── datasets.py            # Dataset upload + processing
│       ├── events.py              # Cloud event queries
│       ├── users.py               # System user management
│       ├── anomalies.py           # Detection train/infer + anomaly CRUD
│       ├── risk.py                # Risk score queries
│       ├── incidents.py           # Incident management
│       ├── alerts.py              # Alert acknowledgement
│       ├── graph.py               # Graph window inspection
│       ├── reports.py             # Security reports
│       └── evaluation.py          # Eval results + dashboard summary
├── data/
│   ├── demo/                      # Demo dataset + ground truth
│   ├── raw/                       # Uploaded raw files
│   └── processed/                 # (reserved for future use)
├── models/
│   ├── trained/                   # Saved model state dicts
│   └── checkpoints/               # Training checkpoints
├── tests/
│   ├── conftest.py                # Async SQLite fixtures + auth
│   ├── test_auth.py
│   ├── test_datasets.py
│   ├── test_feature_engineering.py
│   ├── test_graph_builder.py
│   ├── test_risk_scorer.py
│   ├── test_adaptive_window.py
│   ├── test_coordinated_detection.py
│   └── test_predictor.py
├── .env.example
├── requirements.txt
├── requirements-test.txt
├── pytest.ini
├── Dockerfile
└── docker-compose.yml
```

---

## Requirements

- Python 3.11+
- PostgreSQL 14+ (or Docker)
- PyTorch 2.3 (CPU) — optional, falls back to sklearn if unavailable

---

## Quick Start (Docker)

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env: change SECRET_KEY and ADMIN_PASSWORD

# 2. Start services
docker compose up --build

# 3. API is available at http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

---

## Quick Start (Local)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL pointing to your PostgreSQL instance

# 4. Start the API
uvicorn app.main:app --reload --port 8000

# 5. Interactive docs at http://localhost:8000/docs
```

---

## Configuration

All settings are loaded from environment variables (or a `.env` file). Key settings:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string (asyncpg) |
| `SECRET_KEY` | — | JWT signing secret (**must be changed**) |
| `ADMIN_PASSWORD` | — | Seed admin password (**must be changed**) |
| `DEMO_MODE` | `false` | Auto-loads demo dataset on startup |
| `DEFAULT_WINDOW_HOURS` | `24` | Fixed window duration |
| `ADAPTIVE_LOW_THRESHOLD` | `100` | Events below this → 48h window |
| `ADAPTIVE_HIGH_THRESHOLD` | `1000` | Events above this → 6h window |
| `GNN_HIDDEN_DIM` | `64` | GNN hidden layer dimension |
| `ANOMALY_THRESHOLD` | `0.5` | Default detection threshold |

---

## API Reference

All routes are under `/api/v1/`. Authentication is Bearer JWT.

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login (OAuth2 form), returns JWT |
| POST | `/auth/register` | Register new user (Admin only) |

### Datasets
| Method | Path | Description |
|--------|------|-------------|
| POST | `/datasets/upload` | Upload CSV/JSON dataset |
| GET | `/datasets` | List all datasets |
| GET | `/datasets/{id}` | Get dataset details |
| POST | `/datasets/{id}/process` | Preprocess + build graph windows |

### Anomaly Detection
| Method | Path | Description |
|--------|------|-------------|
| POST | `/detection/models/train` | Train model on a dataset |
| POST | `/detection/models/infer` | Run inference on a graph window |
| GET | `/detection/anomalies` | List anomalies |
| GET | `/detection/anomalies/{id}` | Get anomaly detail + explanation |

### Risk Scores
| Method | Path | Description |
|--------|------|-------------|
| GET | `/risk` | List risk scores |
| POST | `/risk/compute/{anomaly_id}` | Compute risk for an anomaly |
| GET | `/risk/user/{uid}/history` | Risk history for a cloud user |

### Incidents & Alerts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/incidents` | List incidents |
| POST | `/incidents` | Create incident from anomaly |
| PATCH | `/incidents/{id}/status` | Update incident status |
| GET | `/alerts` | List alerts |
| PATCH | `/alerts/{id}/acknowledge` | Acknowledge alert |

### Reports & Evaluation
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports/security` | Security summary report |
| GET | `/evaluation/results` | Model evaluation results |
| GET | `/evaluation/dashboard/summary` | Real-time dashboard aggregates |

---

## ML Pipeline

### Baseline Model
- **Type:** Static 2-layer GCN (single snapshot)
- **Training:** Unsupervised reconstruction loss (MSE)
- **Scoring:** Isolation Forest over GCN embeddings
- **Threshold:** Statistical (mean + 2σ), adaptive, or fixed

### Enhanced Model
- **Type:** Multi-layer GCN/GAT + Multi-head Temporal Attention
- **Additions:** Edge temporal weighting, multi-window aggregation
- **GNNExplainer:** Integration stub present, not yet deployed

### Risk Scoring Weights (sum to 100)
| Factor | Max Contribution |
|--------|-----------------|
| Anomaly score | 30 |
| Behavioral deviation | 15 |
| Unusual service access | 15 |
| Sensitive resource access | 10 |
| Failed request ratio | 10 |
| Request frequency | 8 |
| Coordinated behavior | 7 |
| Temporal anomaly | 5 |

---

## Demo Dataset

Located at `data/demo/sample_cloudtrail.csv`. Contains 100 events across 7 users:
- **U001–U005:** Normal business-hours activity
- **U006:** Off-hours IAM + Secrets Manager + KMS access, high failure rate
- **U007:** Very high-frequency multi-service reconnaissance pattern

Ground truth labels: `data/demo/ground_truth_labels.json`

> **Note:** All anomaly labels are observational. No attack categories are
> invented. Coordinated detection is heuristic-based, not causal.

---

## Running Tests

```bash
pip install -r requirements-test.txt
pytest tests/ -v --tb=short
```

Tests use an in-memory SQLite database. No PostgreSQL required for tests.

---

## Design Decisions and Limitations

1. **Baseline is not a paper reproduction.** The baseline GCN is a standard
   implementation used for comparison. It is not claimed to be identical to
   any published system.

2. **No fake predictions.** The early-warning predictor returns
   `prediction_available=false` when fewer than 3 historical data points
   exist. No synthetic predictions are generated.

3. **No attack labels.** The coordinated detector outputs factual behavioral
   overlap evidence only. Words like "exfiltration" or "privilege escalation"
   are never assigned as labels.

4. **No real cloud actions.** All recommendations are simulation-only.
   `is_simulation_only=True` is always set. The system never modifies AWS
   permissions.

5. **Explainability is observational.** Rule-based explanations describe what
   was observed in the data. They are not claimed to be mathematically causal.

6. **PyTorch optional.** If PyTorch or PyG is unavailable, the system falls
   back to sklearn-only anomaly detection (Isolation Forest on raw features).

---

## Roadmap

- **Phase 2:** GNNExplainer integration, Streaming ingestion (Kafka), LSTM predictor
- **Phase 3:** Frontend dashboard, Webhook alerts, Alembic migrations, CI/CD pipeline
