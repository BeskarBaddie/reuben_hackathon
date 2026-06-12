from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health import router as health_router
from shared.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database.session import init_db

    try:
        init_db()
    except Exception:
        # Allow the API to boot without a database so /health can report status.
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FarmWise — Climate Intelligence for Smallholder Farmers",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
