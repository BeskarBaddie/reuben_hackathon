from fastapi import APIRouter
from sqlalchemy import text

from database.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    try:
        with engine.connect() as conn:
            postgis = conn.execute(text("SELECT PostGIS_Version()")).scalar()
        database = {"connected": True, "postgis": postgis}
    except Exception as exc:  # pragma: no cover - depends on local infra
        database = {"connected": False, "error": str(exc)}
    return {"status": "ok", "database": database}
