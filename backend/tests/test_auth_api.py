"""Pruebas de la API de autenticación contra PostgreSQL real (RF-AUT-01 a RF-AUT-04)."""
import re
import uuid

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.base import ahora_utc
from app.db.session import get_db
from app.main import app
from app.models import Usuario
from app.services.correo import remitente

CLAVE = "Clave-segura-2026"
NUEVA = "Otra-clave-segura-2027"
BASE = "/api/v1/auth"


@pytest.fixture
def cliente(session, monkeypatch: pytest.MonkeyPatch):
    # TestClient usa http://testserver; las cookies Secure no viajarían sobre http en la prueba.
    monkeypatch.setattr(settings, "cookie_secure", False)
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def correo_nuevo() -> str:
    return f"{uuid.uuid4().hex[:12]}@ejemplo.co"


def token_del_ultimo_correo(correo: str) -> str:
    mensaje = remitente.ultimo_para(correo)
    assert mensaje is not None, "No se envió correo a esa dirección"
    return re.search(r"token=([A-Za-z0-9_\-]+)", mensaje.cuerpo).group(1)


def registrar_y_verificar(cliente: TestClient, correo: str) -> None:
    assert cliente.post(f"{BASE}/register", json={"correo": correo, "clave": CLAVE}).status_code == 202
    assert cliente.post(f"{BASE}/verify-email", json={"token": token_del_ultimo_correo(correo)}).status_code == 200


def refrescar_con(cliente: TestClient, refresco: str):
    """Envía un refresh token concreto, ignorando la cookie guardada en el cliente."""
    return cliente.post(f"{BASE}/refresh", headers={"Cookie": f"refresh_token={refresco}"})


def test_registro_responde_igual_exista_o_no_el_correo(cliente: TestClient) -> None:
    correo = correo_nuevo()
    primera = cliente.post(f"{BASE}/register", json={"correo": correo, "clave": CLAVE})
    segunda = cliente.post(f"{BASE}/register", json={"correo": correo, "clave": CLAVE})
    assert primera.status_code == segunda.status_code == 202
    assert primera.json() == segunda.json()


def test_registro_rechaza_contrasena_debil(cliente: TestClient) -> None:
    respuesta = cliente.post(f"{BASE}/register", json={"correo": correo_nuevo(), "clave": "corta"})
    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith("application/problem+json")


def test_no_inicia_sesion_sin_verificar(cliente: TestClient) -> None:
    correo = correo_nuevo()
    cliente.post(f"{BASE}/register", json={"correo": correo, "clave": CLAVE})
    respuesta = cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    assert respuesta.status_code == 403


def test_verificacion_de_un_solo_uso(cliente: TestClient) -> None:
    correo = correo_nuevo()
    cliente.post(f"{BASE}/register", json={"correo": correo, "clave": CLAVE})
    token = token_del_ultimo_correo(correo)
    assert cliente.post(f"{BASE}/verify-email", json={"token": token}).status_code == 200
    assert cliente.post(f"{BASE}/verify-email", json={"token": token}).status_code == 400


def test_login_entrega_token_y_cookie_httponly(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    respuesta = cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]
    cookie = respuesta.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_me_requiere_token_de_acceso(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    assert cliente.get(f"{BASE}/me").status_code == 401

    acceso = cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE}).json()["access_token"]
    respuesta = cliente.get(f"{BASE}/me", headers={"Authorization": f"Bearer {acceso}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == correo


def test_bloqueo_tras_cinco_intentos_fallidos(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    for _ in range(5):
        assert cliente.post(f"{BASE}/login", json={"correo": correo, "clave": "mal-intento-1"}).status_code == 401
    # Ni siquiera la contraseña correcta funciona durante el bloqueo, y la respuesta es la de una credencial incorrecta.
    assert cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE}).status_code == 401


def test_respuesta_de_bloqueo_igual_a_cuenta_inexistente(cliente: TestClient) -> None:
    # Un atacante no debe poder saber qué correos existen ni cuáles están bloqueados.
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    for _ in range(5):
        cliente.post(f"{BASE}/login", json={"correo": correo, "clave": "mal-intento-1"})
    bloqueada = cliente.post(f"{BASE}/login", json={"correo": correo, "clave": "mal-intento-1"})
    inexistente = cliente.post(f"{BASE}/login", json={"correo": correo_nuevo(), "clave": "mal-intento-1"})
    assert bloqueada.status_code == inexistente.status_code == 401
    assert bloqueada.json() == inexistente.json()


def test_la_cuenta_se_desbloquea_al_vencer_el_bloqueo(cliente: TestClient, session) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    for _ in range(5):
        cliente.post(f"{BASE}/login", json={"correo": correo, "clave": "mal-intento-1"})
    usuario = session.scalar(select(Usuario).where(Usuario.correo == correo))
    usuario.bloqueado_hasta = ahora_utc() - timedelta(minutes=1)
    session.commit()
    assert cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE}).status_code == 200


def test_refresh_rota_el_token(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    primero = cliente.cookies.get("refresh_token")

    assert cliente.post(f"{BASE}/refresh").status_code == 200
    segundo = cliente.cookies.get("refresh_token")
    assert segundo and segundo != primero


def test_reutilizar_refresh_viejo_cierra_todas_las_sesiones(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    viejo = cliente.cookies.get("refresh_token")
    cliente.post(f"{BASE}/refresh")
    nuevo = cliente.cookies.get("refresh_token")

    # Reutilizar el token ya rotado: se asume robo.
    assert refrescar_con(cliente, viejo).status_code == 401
    # Incluso el token vigente queda invalidado.
    assert refrescar_con(cliente, nuevo).status_code == 401


def test_logout_invalida_el_refresh(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    refresco = cliente.cookies.get("refresh_token")

    assert cliente.post(f"{BASE}/logout").status_code == 200
    assert refrescar_con(cliente, refresco).status_code == 401


def test_recuperacion_cambia_clave_y_cierra_sesiones(cliente: TestClient) -> None:
    correo = correo_nuevo()
    registrar_y_verificar(cliente, correo)
    cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE})
    refresco_anterior = cliente.cookies.get("refresh_token")

    assert cliente.post(f"{BASE}/forgot-password", json={"correo": correo}).status_code == 202
    token = token_del_ultimo_correo(correo)

    # Una contraseña débil se rechaza sin gastar el enlace.
    assert cliente.post(f"{BASE}/reset-password", json={"token": token, "clave": "corta"}).status_code == 422
    assert cliente.post(f"{BASE}/reset-password", json={"token": token, "clave": NUEVA}).status_code == 200

    assert refrescar_con(cliente, refresco_anterior).status_code == 401
    assert cliente.post(f"{BASE}/login", json={"correo": correo, "clave": CLAVE}).status_code == 401
    assert cliente.post(f"{BASE}/login", json={"correo": correo, "clave": NUEVA}).status_code == 200


def test_recuperacion_responde_igual_para_correo_inexistente(cliente: TestClient) -> None:
    existente = correo_nuevo()
    registrar_y_verificar(cliente, existente)
    a = cliente.post(f"{BASE}/forgot-password", json={"correo": existente})
    b = cliente.post(f"{BASE}/forgot-password", json={"correo": correo_nuevo()})
    assert a.status_code == b.status_code == 202
    assert a.json() == b.json()
