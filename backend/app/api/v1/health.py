"""Endpoint de salud (RF-ADM-01).

Responde sin datos sensibles. Sirve para monitoreo y para despertar el backend
en Render (documento §14.2).
"""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["operación"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
    }
