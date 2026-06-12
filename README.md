# FarmWise — Climate Intelligence Platform for Smallholder Farmers

AI-powered decision support for small-scale farmers adapting to climate change.
See [CLAUDE.md](CLAUDE.md) for the full architecture spec.

## Local development

### 1. Infrastructure (PostgreSQL + PostGIS, Redis)

```bash
docker compose up -d
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs — health check: http://localhost:8000/health

### 3. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

### Tests

```bash
cd backend
pytest
```

## Structure

- `backend/` — FastAPI modular monolith (farms, geospatial, climate, predictions, recommendations)
- `frontend/` — Next.js + TypeScript + Leaflet
- `docker-compose.yml` — local PostGIS + Redis
