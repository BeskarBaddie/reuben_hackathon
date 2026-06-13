# Climate Intelligence Platform

AI-assisted climate decision support for smallholder farmers. Phase 1 is a modular monolith with a FastAPI backend and a Next.js frontend.

## Architecture

- `backend/`: FastAPI modular monolith
  - `auth`: user identity contracts
  - `farms`: farm profiles, crop data, planting dates, irrigation and boundaries
  - `geospatial`: polygon validation, area calculation and boundary operations
  - `analysis`: asynchronous analysis contracts and job status
  - `recommendations`: LLM-facing recommendation wording contracts
- `frontend/`: Next.js app for farm registration and boundary capture
- `infra/`: local development and Cloud Run oriented container wiring

## Local Development

```bash
docker compose up --build
```

Backend: `http://localhost:8000`

Frontend: `http://localhost:3000`

## Sprint 1 Scope

- Create farm profiles
- Validate GeoJSON polygon boundaries
- Store boundaries in PostgreSQL/PostGIS
- Expose REST API contracts
- Provide a frontend farm registration workflow

LLMs are intentionally not used for geospatial analysis, climate calculations, or risk scoring.

## Phase 2 Setup: Earth Engine

The app currently defaults to `REMOTE_SENSING_PROVIDER=mock`, which produces deterministic placeholder NDVI results so the end-to-end workflow can be tested without cloud credentials.

To switch to real satellite analysis:

1. Create or choose a Google Cloud project.
2. Enable the Earth Engine API for that project.
3. Register the project for Earth Engine access.
4. Create a service account for backend analysis jobs.
5. Grant the service account Earth Engine access and the minimum IAM roles required by your project.
6. Create a JSON key for local development, or use Cloud Run service identity in production.
7. Set:

```bash
REMOTE_SENSING_PROVIDER=earth_engine
EARTH_ENGINE_PROJECT_ID=your-gcp-project-id
EARTH_ENGINE_SERVICE_ACCOUNT_EMAIL=service-account@your-project.iam.gserviceaccount.com
EARTH_ENGINE_SERVICE_ACCOUNT_KEY_PATH=/absolute/path/to/service-account-key.json
EARTH_ENGINE_DAYS_LOOKBACK=45
```

For Cloud Run, prefer Workload Identity / attached service account credentials instead of shipping JSON keys. In that case, keep `EARTH_ENGINE_PROJECT_ID` set and omit the key path variables.

## Phase 2 API

Start farm analysis:

```http
POST /api/v1/farms/{farm_id}/analyses
```

Response:

```json
{
  "analysis_id": "123",
  "status": "processing"
}
```

Fetch analysis:

```http
GET /api/v1/analyses/{analysis_id}
```

Current outputs:

- NDVI
- Vegetation health
- Water stress
- Source dataset/provider
- Evidence metadata

The Earth Engine adapter uses Sentinel-2 Surface Reflectance Harmonized imagery and computes NDVI from bands `B8` and `B4`.

## Phase 3 Climate Intelligence

The analysis job now also produces deterministic climate summaries:

- Rainfall this season
- Historical rainfall average for the same seasonal window
- Rainfall anomaly percentage
- Mean temperature this season
- Historical mean temperature
- Temperature anomaly
- Simple climate signal label

Earth Engine datasets:

- Rainfall: `UCSB-CHG/CHIRPS/DAILY`, band `precipitation`
- Temperature: `ECMWF/ERA5_LAND/DAILY_AGGR`, band `temperature_2m`

Default comparison window:

```bash
CLIMATE_SEASON_DAYS=90
CLIMATE_BASELINE_START_YEAR=2001
CLIMATE_BASELINE_END_YEAR=2020
```

The climate module performs deterministic calculations only. LLMs are not used for climate anomaly calculations.

## Mapbox Setup

Create a Mapbox public access token for browser map rendering and geocoding.

For the Next.js app:

```bash
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your_public_mapbox_token
```

For the current static local launcher, create `frontend/static/config.js` from `frontend/static/config.example.js`:

```js
window.CLIMATE_APP_CONFIG = {
  MAPBOX_TOKEN: "pk.your_public_mapbox_token"
};
```

Recommended Mapbox token restrictions:

- URL restrictions for local development:
  - `http://localhost:3000/*`
  - `http://127.0.0.1:3000/*`
  - `http://localhost:8080/*`
  - `http://127.0.0.1:8080/*`
- Production domain restriction once deployed.
- Token scopes:
  - public map rendering
  - geocoding/search access

Do not use a secret Mapbox token in browser code. Use a public `pk.*` token only.

## Phase 5 Recommendations

Recommendations are generated after an analysis completes. The recommendation module uses deterministic fallback rules by default:

```bash
RECOMMENDATION_PROVIDER=deterministic
```

To use OpenAI for farmer-friendly wording while preserving deterministic risk calculations:

```bash
RECOMMENDATION_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.5
```

The LLM receives only the stored evidence snapshot and must return JSON matching the recommendation schema. It does not calculate NDVI, climate anomalies, or risk scores.

API:

```http
POST /api/v1/analyses/{analysis_id}/recommendations
GET /api/v1/analyses/{analysis_id}/recommendations
```

The static local UI is now split into:

- Dashboard
- Register
- Report
- Recommendations
