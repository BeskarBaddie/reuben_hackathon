from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@db:5432/climate",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )
    create_tables_on_startup: bool = Field(default=True, alias="CREATE_TABLES_ON_STARTUP")
    remote_sensing_provider: str = Field(default="mock", alias="REMOTE_SENSING_PROVIDER")
    earth_engine_project_id: str | None = Field(default=None, alias="EARTH_ENGINE_PROJECT_ID")
    earth_engine_service_account_email: str | None = Field(
        default=None,
        alias="EARTH_ENGINE_SERVICE_ACCOUNT_EMAIL",
    )
    earth_engine_service_account_key_path: str | None = Field(
        default=None,
        alias="EARTH_ENGINE_SERVICE_ACCOUNT_KEY_PATH",
    )
    earth_engine_days_lookback: int = Field(default=45, alias="EARTH_ENGINE_DAYS_LOOKBACK")
    climate_provider: str = Field(default="earth_engine", alias="CLIMATE_PROVIDER")
    climate_season_days: int = Field(default=90, alias="CLIMATE_SEASON_DAYS")
    climate_baseline_start_year: int = Field(default=2001, alias="CLIMATE_BASELINE_START_YEAR")
    climate_baseline_end_year: int = Field(default=2020, alias="CLIMATE_BASELINE_END_YEAR")
    forecast_provider: str = Field(default="mock", alias="FORECAST_PROVIDER")
    forecast_horizon_days: int = Field(default=14, alias="FORECAST_HORIZON_DAYS")
    recommendation_provider: str = Field(default="deterministic", alias="RECOMMENDATION_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.5", alias="OPENAI_MODEL")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:latest", alias="OLLAMA_MODEL")
    ollama_embedding_model: str = Field(
        default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL"
    )
    retrieval_grounding_threshold: float = Field(
        default=0.55, alias="RETRIEVAL_GROUNDING_THRESHOLD"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
