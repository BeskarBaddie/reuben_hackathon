# AgriShield

AgriShield is an AI-assisted climate intelligence platform for smallholder farmers. It helps farmers register plots, analyze climate and vegetation risk, retrieve crop-specific guidance, and generate practical adaptation recommendations.

The current build is a modular monolith with a FastAPI backend and a static local frontend. It is designed so modules can later be extracted into services.

## What It Does

- Register farm plots with crop, planting date, expected harvest date, irrigation type, farmer notes, and drawn boundaries.
- Store plot boundaries with PostGIS-compatible geometry.
- Analyze plots with Google Earth Engine:
  - NDVI
  - vegetation health
  - water stress
  - rainfall anomaly
  - temperature anomaly
  - drought, flood, and heat stress scores
- Sync crop guidance documents from Google Drive.
- Use lightweight RAG to retrieve relevant crop guidance for each plot.
- Generate farmer-friendly recommendations with Ollama, OpenAI, or deterministic fallback logic.
- Show a dashboard, plot management, analysis report, recommendations, settings, and dummy community alerts.

## Architecture

- `backend/`: FastAPI modular monolith
  - `auth`: local user identity contract
  - `farms`: plot profiles, crop data, planting/harvest dates, irrigation, notes, boundaries
  - `geospatial`: polygon validation, area calculation, geometry handling
  - `analysis`: Earth Engine analysis jobs and risk outputs
  - `climate`: rainfall and temperature anomaly summaries
  - `risk`: deterministic drought, flood, and heat scoring
  - `knowledge`: Google Drive sync, document parsing, chunking, and retrieval
  - `recommendations`: LLM prompts, recommendation generation, specificity layer
- `frontend/static/`: local browser UI using Mapbox GL JS
- `infra/`: deployment-oriented infrastructure placeholders

## AI Models And Techniques

AgriShield separates deterministic analysis from language generation.

LLMs are used for:

- recommendation wording
- farmer-friendly explanations
- summarization of evidence into practical actions

LLMs are not used for:

- NDVI calculation
- climate anomaly calculation
- geospatial analysis
- farm boundary detection
- risk scoring

Current AI/model options:

- **Ollama local LLM**: default local option, tested with `llama3.1:latest`
- **OpenAI API**: optional provider through `RECOMMENDATION_PROVIDER=openai`
- **Deterministic fallback**: rule-based recommendations if an LLM is unavailable

Techniques used:

- **RAG over Google Drive**: crop documents are synced, parsed, chunked, stored, searched, and only relevant chunks are passed to the LLM.
- **Keyword/metadata retrieval**: current retrieval uses crop, risk drivers, farmer notes, irrigation, and climate signals rather than vector embeddings.
- **Structured JSON generation**: recommendations must match a strict schema.
- **Prompt constraints**: the LLM must not invent data and must say `insufficient data` when evidence is missing.
- **Deterministic risk scoring**: drought, flood, and heat scores come from code, not the LLM.
- **Specificity layer**: after LLM generation, backend logic makes recommendations more actionable using farm notes, risk evidence, crop stage, and retrieved source names.

Future AI improvements:

- vector embeddings for semantic retrieval
- OCR for scanned PDFs
- multilingual summaries
- farmer Q&A over the indexed knowledge base
- better source ranking by crop, geography, season, and document quality

## External Services

Required for full functionality:

- Google Earth Engine through a Google Cloud project
- Google Drive API for knowledge-base document sync
- Mapbox public token for browser maps and location search
- Ollama locally, or OpenAI API if using OpenAI recommendations

## Local Run Instructions

### 1. Backend Environment

Create or update `backend/.env`.

For local SQLite testing:

```env
DATABASE_URL=sqlite:///./local.db
CORS_ORIGINS=["http://localhost:8080","http://127.0.0.1:8080","null"]
```

For PostgreSQL/PostGIS:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/climate
```

Earth Engine:

```env
REMOTE_SENSING_PROVIDER=earth_engine
EARTH_ENGINE_PROJECT_ID=your-gcp-project-id
EARTH_ENGINE_SERVICE_ACCOUNT_EMAIL=service-account@your-project.iam.gserviceaccount.com
EARTH_ENGINE_SERVICE_ACCOUNT_KEY_PATH=/absolute/path/to/service-account-key.json
EARTH_ENGINE_DAYS_LOOKBACK=45
```

Climate defaults:

```env
CLIMATE_SEASON_DAYS=90
CLIMATE_BASELINE_START_YEAR=2001
CLIMATE_BASELINE_END_YEAR=2020
```

Ollama recommendations:

```env
RECOMMENDATION_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:latest
```

Google Drive knowledge base:

```env
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY_PATH=/absolute/path/to/service-account-key.json
GOOGLE_DRIVE_FOLDER_IDS=["your_google_drive_folder_id"]
KNOWLEDGE_MAX_CHUNKS=6
```

Use the folder ID from:

```text
https://drive.google.com/drive/folders/THIS_IS_THE_FOLDER_ID
```

The backend also accepts a full Google Drive folder URL.

### 2. Frontend Mapbox Config

Create `frontend/static/config.js` from `frontend/static/config.example.js`:

```js
window.CLIMATE_APP_CONFIG = {
  MAPBOX_TOKEN: "pk.your_mapbox_public_token_here"
};
```

Use a public `pk.*` Mapbox token only. Do not put secret tokens in frontend files.

### 3. Start Ollama

```bash
/opt/homebrew/bin/ollama serve
```

Or, if `ollama` is on your `PATH`:

```bash
ollama serve
```

Make sure the model exists:

```bash
ollama pull llama3.1
ollama list
```

### 4. Start Backend

From the repo root:

```bash
cd backend
DATABASE_URL=sqlite:///./local.db ../.venv312/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### 5. Start Frontend

From the repo root:

```bash
cd frontend/static
python3 -m http.server 8080 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8080
```

## Knowledge Base Sync

Make sure:

- Google Drive API is enabled.
- The service account has access to the Drive folder.
- The folder ID is configured in `backend/.env`.

Sync documents:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/sync \
  -H "Content-Type: application/json" \
  -d '{"max_files":50}'
```

Search retrieved guidance:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query":"maize drought rainfed water stress","crop":"maize","limit":6}'
```

Supported document types:

- Google Docs, exported as text
- text, Markdown, CSV
- PDF through `pypdf`
- DOCX through `python-docx`

Scanned PDFs may need OCR before text can be indexed.

## Main API Endpoints

Create plot:

```http
POST /api/v1/farms
```

List plots:

```http
GET /api/v1/farms
```

Delete plot:

```http
DELETE /api/v1/farms/{farm_id}
```

Start analysis:

```http
POST /api/v1/farms/{farm_id}/analyses
```

Get analysis:

```http
GET /api/v1/analyses/{analysis_id}
```

Generate recommendations:

```http
POST /api/v1/analyses/{analysis_id}/recommendations
```

Get latest recommendation for an analysis:

```http
GET /api/v1/analyses/{analysis_id}/recommendations
```

Get latest saved recommendation for the user:

```http
GET /api/v1/recommendations/latest
```

Sync knowledge:

```http
POST /api/v1/knowledge/sync
```

Search knowledge:

```http
POST /api/v1/knowledge/search
```

For local testing, requests use:

```http
X-User-Id: 11111111-1111-4111-8111-111111111111
```

## Current UI

The current browser UI includes:

- Dashboard
- Plots
- Plot profile
- Analysis report
- Recommendations
- Community alerts
- Settings

Community alerts are currently a dummy frontend feature. They surface seeded nearby alerts and farmer-note-derived alerts within a displayed 50 km² community zone. A production version should use a backend `community_alerts` table plus PostGIS radius queries.

## Testing

Run focused backend tests:

```bash
cd backend
../.venv312/bin/python -m pytest tests/test_knowledge.py tests/test_recommendations.py
```

Compile backend Python:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/reuben_pycache .venv312/bin/python -m compileall backend/app backend/tests backend/alembic
```

Check frontend inline JavaScript syntax:

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('frontend/static/index.html','utf8'); const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]); for (const script of scripts) new Function(script); console.log('inline scripts ok');"
```

## Deployment Direction

Preferred cloud: Google Cloud Platform.

Suggested services:

- Cloud Run for FastAPI backend and future workers
- Cloud SQL PostgreSQL with PostGIS
- Cloud Storage for reports and cached exports
- Pub/Sub for future event-driven analysis workflows
- Memorystore Redis for future background job/cache needs
- Artifact Registry for containers

For production:

- use Postgres/PostGIS instead of SQLite
- use Cloud Run service identity instead of local JSON keys
- move long-running analysis to worker queues
- add authentication
- persist community alerts server-side
- add monitoring, audit logs, and rate limits
