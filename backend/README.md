# Agent 63 – Backend Service

FastAPI backend foundation for the Agent 63 Secure Institutional Data Analytics Agent.

> [!NOTE]
> **PostgreSQL is NOT required for local development or testing in Phase 2.**
> The backend runs and passes all tests completely without a local PostgreSQL server.

---

## 1. Prerequisites

- Python 3.10+ (Tested on Python 3.14)
- Git

---

## 2. Quickstart

### 2.1 Set Up Virtual Environment

From the project root:

```bash
# Windows
py -3.14 -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2.2 Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2.3 Run Local Development Server

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Once started:
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Readiness Endpoint:** [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

---

## 3. Running Tests

Run the complete backend test suite:

```bash
pytest backend/tests -v
```

All 24 test cases run entirely in-memory and execute in under 1 second.
