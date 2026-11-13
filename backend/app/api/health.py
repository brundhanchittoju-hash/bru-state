from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """System health check and environmental capabilities disclosure."""
    db_mode = "sqlite_fallback" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database_mode": db_mode,
        "ocr_mode": "text_layer_fallback",
        "state": settings.DEFAULT_STATE,
        "demo_data_enabled": True,
    }
