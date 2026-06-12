# Climate Intelligence Platform for Smallholder Farmers

AI-powered web platform helping small-scale farmers in LMICs adapt to climate change.
Core loop: farmer draws farm boundary → platform analyzes vegetation/soil/water/climate →
returns risk scores, seasonal outlooks, and plain-language adaptation recommendations.
This is **decision support**, not a weather display.

## Architecture

- **Phase 1 = modular monolith** (NOT microservices). Service boundaries are module
  boundaries, extractable later. Clean architecture, DDD, RESTful APIs.
- Long-running analyses are async: API immediately returns
  `{ "analysis_id": "...", "status": "processing" }`; clients poll or subscribe.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript + React Query; Leaflet for map/polygon drawing |
| Backend | Python + FastAPI |
| Database | PostgreSQL + **PostGIS (required)** — Cloud SQL in prod |
| Background jobs | Redis + Celery (Memorystore in prod) |
| Cloud | GCP: Cloud Run (API + workers), Cloud Storage, Pub/Sub, Artifact Registry |
| Geospatial libs | Shapely, GeoPandas, Rasterio, Google Earth Engine |

## Backend layout

```
backend/
├── api/              # FastAPI routers, request/response schemas
├── farms/            # farm profiles, boundaries, crops, planting dates, irrigation
├── geospatial/       # polygon validation, area calc, raster clipping
├── remote_sensing/   # Earth Engine: NDVI, water indices, vegetation trends
├── climate/          # historical climate, rainfall/temp anomalies, forecasts
├── predictions/      # risk models, climate risk scoring (deterministic/ML — NO LLMs)
├── recommendations/  # LLM-generated recommendations, prioritization, explanations
├── workers/          # Celery tasks
├── database/         # models, migrations, session management
├── shared/           # cross-cutting utilities
└── tests/
```

## LLM usage rules (strict)

LLMs ONLY for: summarization, explanation, recommendation wording, translation, farmer Q&A.
LLMs NEVER for: NDVI calculation, climate anomalies, geospatial analysis, risk scoring,
farm boundaries — those must be deterministic code or ML models.

Recommendation prompts must: never invent data, cite provided evidence, return JSON only,
use farmer-friendly language, say "insufficient data" when inputs are missing.

## Sprint plan

1. **Farm registration** — auth, farm CRUD, boundary drawing, PostGIS storage
2. **Farm analysis** — Earth Engine integration, NDVI over polygon → basic health report
3. **Climate intelligence** — historical retrieval, rainfall anomalies, "this season vs average"
4. **Risk scoring** — drought / flood / heat stress → risk dashboard
5. **AI recommendations** — recommendation service, structured prompts, prioritized actions

## Code standards

Clean architecture, SOLID, FastAPI best practices, PostGIS-compatible SQL, testable,
production-ready, clear API contracts, Dockerized for Cloud Run. Propose improvements
when architectural weaknesses are spotted.
