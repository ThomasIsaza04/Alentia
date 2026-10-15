"""Pruebas del endpoint de salud y de las cabeceras de seguridad."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_ok() -> None:
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"


def test_health_no_expone_datos_sensibles() -> None:
    cuerpo = client.get("/health").json()
    assert set(cuerpo.keys()) == {"status", "version", "environment"}


def test_cabeceras_de_seguridad_presentes() -> None:
    respuesta = client.get("/health")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert respuesta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
