import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, RateLimitExceeded
from app.core.logging import configure_logging
from app.repositories.contact_repository import ContactRepository
from app.repositories.rate_limit_repository import RateLimitRepository
from app.services.ai_service import AIService
from app.services.contact_service import ContactService
from app.services.email_service import EmailService

logger = logging.getLogger("requests")
STATIC_DIR = Path(__file__).parent / "static"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def request_id_from(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    if REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.ensure_directories()
    configure_logging(settings)

    contacts = ContactRepository(settings.database_path)
    rate_limits = RateLimitRepository(settings.database_path)
    ai = AIService(settings.openai_api_key, settings.openai_model, settings.ai_timeout_seconds)
    email = EmailService(
        mode=settings.email_mode,
        log_path=settings.email_log_path,
        owner_email=settings.owner_email,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        smtp_use_tls=settings.smtp_use_tls,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        contacts.initialize()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Contact API with AI classification, resilient fallback, email, and metrics.",
        docs_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.contact_repository = contacts
    app.state.contact_service = ContactService(settings, contacts, rate_limits, ai, email)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request_id_from(request)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "Unhandled request error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration,
                },
            )
            raise
        duration = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration,
            },
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimitExceeded):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid input",
                    "details": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                }
            },
        )

    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/docs", include_in_schema=False)
    async def docs():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url=(
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.11/swagger-ui-bundle.js"
            ),
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.11/swagger-ui.css",
            swagger_favicon_url="/static/favicon.svg",
        )

    @app.get("/", include_in_schema=False)
    async def landing() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
