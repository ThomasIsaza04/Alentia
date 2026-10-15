"""Punto de entrada de la API de Alentia.

Ejecutar en local:  uvicorn app.main:app --reload
Documentación OpenAPI: http://localhost:8000/docs (RNF17)
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.acceso_temporal import router as acceso_temporal_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cuenta import router as cuenta_router
from app.api.v1.recordatorios import router as recordatorios_router
from app.api.v1.health import router as health_router
from app.api.v1.perfiles import router as perfiles_router
from app.api.v1.salud import router as salud_router
from app.api.v1.perfiles import router_invitaciones, router_zonas
from app.core.config import settings
from app.core.errores import ErrorAuth
from app.core.security_headers import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.exception_handler(ErrorAuth)
    async def _error_de_autenticacion(request: Request, exc: ErrorAuth) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": exc.titulo,
                "status": exc.status_code,
                "detail": exc.detalle,
            },
            media_type="application/problem+json",
        )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(perfiles_router, prefix="/api/v1")
    app.include_router(router_zonas, prefix="/api/v1")
    app.include_router(router_invitaciones, prefix="/api/v1")
    app.include_router(salud_router)
    app.include_router(acceso_temporal_router)
    app.include_router(cuenta_router)
    app.include_router(recordatorios_router)
    return app


app = create_app()
