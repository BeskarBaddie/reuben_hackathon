from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine
from app.modules.analysis.router import router as analysis_router
from app.modules.farms.router import router as farms_router
from app.modules.recommendations.router import router as recommendations_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Climate Intelligence API",
        version="0.1.0",
        description="Farm-level climate risk analysis and adaptation decision support.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(farms_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(recommendations_router, prefix="/api/v1")

    @app.on_event("startup")
    def create_tables_for_local_development() -> None:
        if settings.create_tables_on_startup:
            if not settings.database_url.startswith("sqlite"):
                with engine.begin() as connection:
                    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            Base.metadata.create_all(bind=engine)
            if settings.database_url.startswith("sqlite"):
                sync_sqlite_schema_for_local_development()

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def sync_sqlite_schema_for_local_development() -> None:
    inspector = inspect(engine)
    if "farm_analyses" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("farm_analyses")}
    desired_columns = {
        "climate_season_start": "VARCHAR(32)",
        "climate_season_end": "VARCHAR(32)",
        "rainfall_this_season_mm": "FLOAT",
        "rainfall_historical_average_mm": "FLOAT",
        "rainfall_anomaly_percent": "FLOAT",
        "temperature_this_season_c": "FLOAT",
        "temperature_historical_average_c": "FLOAT",
        "temperature_anomaly_c": "FLOAT",
        "climate_signal": "VARCHAR(120)",
        "climate_source": "VARCHAR(220)",
        "climate_evidence": "JSON",
        "drought_score": "INTEGER",
        "drought_level": "VARCHAR(40)",
        "drought_drivers": "JSON",
        "flood_score": "INTEGER",
        "flood_level": "VARCHAR(40)",
        "flood_drivers": "JSON",
        "heat_score": "INTEGER",
        "heat_level": "VARCHAR(40)",
        "heat_drivers": "JSON",
        "overall_risk_level": "VARCHAR(40)",
    }
    with engine.begin() as connection:
        for column_name, column_type in desired_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE farm_analyses ADD COLUMN {column_name} {column_type}")
                )

    if "recommendations" in inspector.get_table_names():
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE recommendations (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    analysis_id CHAR(32) NOT NULL,
                    provider VARCHAR(80) NOT NULL,
                    model VARCHAR(120),
                    prompt_version VARCHAR(40) NOT NULL,
                    evidence_snapshot JSON NOT NULL,
                    output JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
