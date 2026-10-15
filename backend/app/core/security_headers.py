"""Cabeceras de seguridad básicas (RNF02, documento §6 y §13.3)."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# La API responde JSON y no necesita recursos externos: se bloquea todo.
CSP_API = "default-src 'none'; frame-ancestors 'none'"
# Swagger UI (/docs) carga su script y estilos desde el CDN que usa FastAPI.
CSP_DOCUMENTACION = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'"
)
RUTAS_DOCUMENTACION = frozenset({"/docs"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Las rutas sensibles (acceso del profesional) fijan no-referrer; no se sobrescribe.
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        es_documentacion = request.url.path in RUTAS_DOCUMENTACION
        response.headers["Content-Security-Policy"] = CSP_DOCUMENTACION if es_documentacion else CSP_API
        return response
