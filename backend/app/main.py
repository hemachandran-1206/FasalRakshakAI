from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .migrations import ensure_schema
from .routers import admin, advisories, auth, cases, catalogue, detect, expert, reports, weather


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "dev" and settings.jwt_secret == "dev-only-secret-change-me-0123456789abcdef":
        raise RuntimeError("Set JWT_SECRET to a long random value before running outside dev")
    Base.metadata.create_all(engine)
    ensure_schema(engine)       # switch to Alembic migrations once the schema stabilises
    if settings.load_models_on_startup:
        from .services.inference import CropForesightPipeline
        app.state.pipeline = CropForesightPipeline()
    yield


app = FastAPI(title="FasalRakshak AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(detect.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(catalogue.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(expert.router, prefix="/api")
app.include_router(advisories.public, prefix="/api")
app.include_router(advisories.staff, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
