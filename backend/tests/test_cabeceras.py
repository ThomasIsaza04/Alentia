"""Cabeceras de seguridad: la API no carga recursos externos; solo /docs usa el CDN de Swagger."""
from fastapi.testclient import TestClient

from app.core.security_headers import CSP_API
from app.main import app


def test_api_usa_csp_estricta() -> None:
    respuesta = TestClient(app).get("/health")
    assert respuesta.headers["content-security-policy"] == CSP_API
    assert "default-src 'none'" in respuesta.headers["content-security-policy"]


def test_documentacion_permite_el_cdn_de_swagger() -> None:
    respuesta = TestClient(app).get("/docs")
    assert respuesta.status_code == 200
    csp = respuesta.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in csp
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
