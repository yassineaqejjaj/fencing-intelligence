from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from fencing_api import __version__
from fencing_api.config import get_settings
from fencing_api.database import SessionLocal
from fencing_api.errors import AppError
from fencing_api.logging_config import configure_logging
from fencing_api.routers import analyses, annotations, auth, catalog, federation, fie, insights, privacy, research, videos
from fencing_api.seed import seed
from fencing_api.storage import ensure_bucket

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.validate_runtime()
    ensure_bucket(settings)
    db = SessionLocal()
    try:
        seed(db)
        db.commit()
    finally:
        db.close()
    if settings.otel_endpoint:
        _configure_otel(settings.otel_endpoint)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Fencing Intelligence API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request validation failed", "details": {"errors": exc.errors()}}})

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/ready")
    def ready():
        checks = {"database": False, "redis": False, "object_storage": False}
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = True
        finally:
            db.close()
        try:
            import redis

            redis.Redis.from_url(settings.redis_url).ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
        try:
            ensure_bucket(settings)
            checks["object_storage"] = True
        except Exception:
            checks["object_storage"] = False
        ok = all(checks.values())
        return JSONResponse(status_code=200 if ok else 503, content={"status": "ready" if ok else "not_ready", "checks": checks})

    for module in (auth, catalog, videos, annotations, insights, analyses, research, privacy, federation, fie):
        app.include_router(module.router, prefix="/api/v1")
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return app


def _configure_otel(endpoint: str) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "fencing-api"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)


app = create_app()
