from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.deps import limiter
from app.api.departments import router as departments_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.settings import router as settings_router
from app.api.audit_trail import router as audit_trail_router
from app.api.users import router as users_router
from app.api.jobs import router as jobs_router
from app.api.verification import router as verification_router
from app.api.findings import router as findings_router
from app.api.finding_reviews import router as finding_reviews_router
from app.api.finding_notes import router as finding_notes_router
from app.api.saved_filters import router as saved_filters_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router
from app.api.search import router as search_router
from app.api.vendors import router as vendors_router
from app.api.reports import router as reports_router
from app.api.public_verify import router as public_verify_router
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DATABASE_URL.startswith("sqlite"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy (allows PDF worker, inline styles for UI/Radix, Supabase endpoints, and configurable CSP_EXTRA)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' blob:",
            "worker-src 'self' blob:",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' blob: data:",
            "font-src 'self' data:",
            "connect-src 'self' blob: data: https://*.supabase.co wss://*.supabase.co",
            "frame-src 'self' blob:",
            "frame-ancestors 'self'",
            "object-src 'none'",
            "base-uri 'self'",
        ]
        if settings.CSP_EXTRA and settings.CSP_EXTRA.strip():
            csp_directives.append(settings.CSP_EXTRA.strip())
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


def create_app() -> FastAPI:
    is_prod = settings.ENVIRONMENT.lower() == "production"
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    # State limiters
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Safe Exception Handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Prevent leaking raw tracebacks to clients
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. This event has been recorded for review.",
                "type": "InternalServerError",
            },
        )

    # Mount Routers under API_V1_STR (/api)
    api_prefix = settings.API_V1_STR
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(cases_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(departments_router, prefix=api_prefix)
    app.include_router(settings_router, prefix=api_prefix)
    app.include_router(audit_trail_router, prefix=api_prefix)
    app.include_router(documents_router, prefix=api_prefix)
    app.include_router(findings_router, prefix=api_prefix)
    app.include_router(finding_reviews_router, prefix=api_prefix)
    app.include_router(finding_notes_router, prefix=api_prefix)
    app.include_router(saved_filters_router, prefix=api_prefix)
    app.include_router(dashboard_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)
    app.include_router(search_router, prefix=api_prefix)
    app.include_router(vendors_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(verification_router, prefix=api_prefix)
    app.include_router(reports_router, prefix=api_prefix)
    app.include_router(public_verify_router, prefix=api_prefix)
    app.include_router(public_verify_router)  # Direct root access /verify/...
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(health_router)  # Direct root access /health

    @app.get("/", tags=["Root"])
    async def root_status():
        return {
            "status": "online",
            "message": "State Audit AI Backend API",
            "health": "/api/health",
            "version": "1.0.0",
        }

    return app


app = create_app()
