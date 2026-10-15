"""Pruebas del acceso temporal por QR y PIN (paso 7) contra PostgreSQL real."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.passwords import verificar
from app.db.session import get_db
from app.main import app
from app.models import AccesoTemporal, EventoAccesoTemporal
from app.services.resumen import construir_resumen
from tests.test_perfiles_api import BASE, cabecera, crear_perfil_de, crear_usuario, dar_acceso

MOVIL = {"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}


@pytest.fixture
def cliente(session):
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def _crear(cliente, titular, perfil_id, categorias=("medicamentos", "sintomas"), duracion=15):
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/accesos-temporales",
        json={"categorias": list(categorias), "duracion_minutos": duracion},
        headers=cabecera(titular),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _abrir_y_verificar(cliente, token, pin, headers=None):
    assert cliente.post(f"{BASE}/acceso-profesional/abrir", json={"token": token}, headers=headers or {}).status_code == 200
    return cliente.post(f"{BASE}/acceso-profesional/verificar", json={"token": token, "pin": pin}, headers=headers or {})


def _bitacora(cliente, titular, acceso_id):
    r = cliente.get(f"{BASE}/accesos-temporales/{acceso_id}/bitacora", headers=cabecera(titular))
    assert r.status_code == 200, r.text
    return [e["tipo"] for e in r.json()]


# ---------- titular ----------

def test_el_token_y_el_pin_no_se_guardan_en_claro(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id)
    token, pin = datos["token"], datos["pin"]

    assert len(pin) == 6 and pin.isdigit()
    assert datos["enlace_path"] == f"/acceso/{token}"
    assert len(token) >= 40  # 256 bits en base64 url

    fila = session.scalar(select(AccesoTemporal).where(AccesoTemporal.id == uuid.UUID(datos["id"])))
    assert fila.hash_token == hashlib.sha256(token.encode()).hexdigest()
    assert fila.hash_token != token
    assert fila.hash_pin != pin
    assert verificar(pin, fila.hash_pin)


def test_lector_no_puede_crear_accesos(cliente, session):
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/accesos-temporales",
        json={"categorias": ["medicamentos"], "duracion_minutos": 15},
        headers=cabecera(lector),
    )
    assert r.status_code == 403


def test_sin_acceso_no_se_listan_los_accesos(cliente, session):
    titular = crear_usuario(session)
    extraño = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _crear(cliente, titular, perfil_id)
    r = cliente.get(f"{BASE}/perfiles/{perfil_id}/accesos-temporales", headers=cabecera(extraño))
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"categorias": ["alergias"], "duracion_minutos": 15},
        {"categorias": ["medicamentos"], "duracion_minutos": 20},
        {"categorias": [], "duracion_minutos": 15},
    ],
)
def test_datos_de_creacion_invalidos_responden_422(cliente, session, cuerpo):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/accesos-temporales", json=cuerpo, headers=cabecera(titular))
    assert r.status_code == 422


# ---------- profesional ----------

def test_flujo_completo_muestra_solo_las_categorias_elegidas(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id, categorias=["medicamentos"])

    r = _abrir_y_verificar(cliente, datos["token"], datos["pin"], headers=MOVIL)
    assert r.status_code == 200, r.text
    sesion = r.json()["sesion_token"]
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["Referrer-Policy"] == "no-referrer"

    res = cliente.get(f"{BASE}/acceso-profesional/resumen", headers={"Authorization": f"Bearer {sesion}"})
    assert res.status_code == 200, res.text
    assert res.headers["Cache-Control"] == "no-store"
    assert res.headers["Referrer-Policy"] == "no-referrer"
    cuerpo = res.json()
    assert [s["clave"] for s in cuerpo["secciones"]] == ["medicamentos"]
    assert "aviso" in cuerpo and "No constituyen un diagnóstico" in cuerpo["aviso"]

    assert _bitacora(cliente, titular, datos["id"]) == ["generado", "abierto", "consumido"]
    eventos = session.scalars(select(EventoAccesoTemporal).where(EventoAccesoTemporal.acceso_id == uuid.UUID(datos["id"]))).all()
    assert {e.tipo_dispositivo for e in eventos} >= {"movil"}


def test_el_enlace_se_consume_una_sola_vez(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id)
    assert _abrir_y_verificar(cliente, datos["token"], datos["pin"]).status_code == 200
    segunda = cliente.post(f"{BASE}/acceso-profesional/verificar", json={"token": datos["token"], "pin": datos["pin"]})
    assert segunda.status_code == 404
    assert segunda.json()["detail"] == "Este acceso no está disponible"
    abrir = cliente.post(f"{BASE}/acceso-profesional/abrir", json={"token": datos["token"]})
    assert abrir.status_code == 404


def test_token_inexistente_responde_mensaje_generico(cliente):
    r = cliente.post(f"{BASE}/acceso-profesional/abrir", json={"token": "x" * 40})
    assert r.status_code == 404
    assert r.json()["detail"] == "Este acceso no está disponible"


def test_cinco_pines_incorrectos_bloquean_el_acceso(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id)
    token, pin = datos["token"], datos["pin"]
    incorrecto = "000000" if pin != "000000" else "111111"
    assert cliente.post(f"{BASE}/acceso-profesional/abrir", json={"token": token}).status_code == 200

    for intento in range(1, 5):
        r = cliente.post(f"{BASE}/acceso-profesional/verificar", json={"token": token, "pin": incorrecto})
        assert r.status_code == 403
        assert f"Te quedan {5 - intento} intentos" in r.json()["detail"]

    quinto = cliente.post(f"{BASE}/acceso-profesional/verificar", json={"token": token, "pin": incorrecto})
    assert quinto.status_code == 404
    correcto = cliente.post(f"{BASE}/acceso-profesional/verificar", json={"token": token, "pin": pin})
    assert correcto.status_code == 404

    tipos = _bitacora(cliente, titular, datos["id"])
    assert tipos.count("pin_fallido") == 5
    assert "bloqueado" in tipos
    assert "consumido" not in tipos


def test_revocar_corta_la_sesion_en_la_siguiente_peticion(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id)
    sesion = _abrir_y_verificar(cliente, datos["token"], datos["pin"]).json()["sesion_token"]
    cabecera_profesional = {"Authorization": f"Bearer {sesion}"}
    assert cliente.get(f"{BASE}/acceso-profesional/resumen", headers=cabecera_profesional).status_code == 200

    r = cliente.post(f"{BASE}/accesos-temporales/{datos['id']}/revocar", headers=cabecera(titular))
    assert r.status_code == 200 and r.json()["estado"] == "revocado"

    despues = cliente.get(f"{BASE}/acceso-profesional/resumen", headers=cabecera_profesional)
    assert despues.status_code == 401
    assert "revocó" in despues.json()["detail"]
    assert "revocado" in _bitacora(cliente, titular, datos["id"])


def test_acceso_vencido_no_se_puede_abrir(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id)
    session.execute(
        update(AccesoTemporal)
        .where(AccesoTemporal.id == uuid.UUID(datos["id"]))
        .values(vence_en=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    session.commit()
    r = cliente.post(f"{BASE}/acceso-profesional/abrir", json={"token": datos["token"]})
    assert r.status_code == 404


def test_la_sesion_no_supera_la_vigencia_del_acceso(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id, duracion=15)
    vence_acceso = datetime.now(timezone.utc) + timedelta(minutes=2)
    session.execute(update(AccesoTemporal).where(AccesoTemporal.id == uuid.UUID(datos["id"])).values(vence_en=vence_acceso))
    session.commit()
    r = _abrir_y_verificar(cliente, datos["token"], datos["pin"])
    sesion_vence = datetime.fromisoformat(r.json()["vence_en"])
    assert sesion_vence <= vence_acceso + timedelta(seconds=1)


def test_sin_sesion_el_resumen_no_responde_datos(cliente):
    r = cliente.get(f"{BASE}/acceso-profesional/resumen")
    assert r.status_code == 401
    assert "PIN" in r.json()["detail"]
    r_falsa = cliente.get(f"{BASE}/acceso-profesional/resumen", headers={"Authorization": "Bearer nada"})
    assert r_falsa.status_code == 401


def test_resumen_sin_registros_no_inventa_contenido(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    datos = _crear(cliente, titular, perfil_id, categorias=("diagnosticos", "medicamentos", "sintomas"))
    sesion = _abrir_y_verificar(cliente, datos["token"], datos["pin"]).json()["sesion_token"]
    cuerpo = cliente.get(f"{BASE}/acceso-profesional/resumen", headers={"Authorization": f"Bearer {sesion}"}).json()
    assert len(cuerpo["secciones"]) == 3
    assert all(s["sin_informacion"] and s["lineas"] == [] for s in cuerpo["secciones"])


def test_resumen_destaca_sintoma_de_tres_dias_seguidos_con_fecha(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    ahora = datetime.now(timezone.utc)
    for horas in (24, 48, 72):
        r = cliente.post(
            f"{BASE}/perfiles/{perfil_id}/sintomas",
            json={"sintoma": "Mareo", "intensidad": 4, "fecha": (ahora - timedelta(hours=horas)).isoformat()},
            headers=cabecera(titular),
        )
        assert r.status_code == 201, r.text
    cliente.post(
        f"{BASE}/perfiles/{perfil_id}/sintomas",
        json={"sintoma": "Tos", "intensidad": 2, "fecha": (ahora - timedelta(hours=12)).isoformat()},
        headers=cabecera(titular),
    )
    datos = _crear(cliente, titular, perfil_id, categorias=("sintomas",))
    sesion = _abrir_y_verificar(cliente, datos["token"], datos["pin"]).json()["sesion_token"]
    cuerpo = cliente.get(f"{BASE}/acceso-profesional/resumen", headers={"Authorization": f"Bearer {sesion}"}).json()
    lineas = cuerpo["secciones"][0]["lineas"]
    mareo = [linea for linea in lineas if linea["texto"].startswith("Mareo")]
    tos = [linea for linea in lineas if linea["texto"].startswith("Tos")]
    assert len(mareo) == 3 and all(linea["destacado"] for linea in mareo)
    assert len(tos) == 1 and not tos[0]["destacado"]
    assert all(len(linea["fecha"]) == 10 for linea in lineas)  # AAAA-MM-DD en cada línea


# ---------- reglas puras del resumen ----------

def test_resumen_puro_solo_incluye_categorias_elegidas():
    from datetime import date

    datos = {
        "diagnosticos": [{"descripcion": "Asma", "fecha": date(2026, 9, 1)}],
        "medicamentos": [{"nombre": "Salbutamol", "dosis": "100 mcg", "desde": date(2026, 9, 2)}],
        "adherencia": {"programadas": 14, "tomadas": 12, "desde": date(2026, 10, 7), "hasta": date(2026, 10, 13)},
        "sintomas": [],
    }
    salida = construir_resumen(["medicamentos", "sintomas"], datos)
    assert [s["clave"] for s in salida["secciones"]] == ["medicamentos", "sintomas"]
    medicamentos = salida["secciones"][0]["lineas"]
    assert medicamentos[1]["texto"].endswith("12 de 14 tomas registradas como tomadas")
    assert medicamentos[1]["fecha"] == "2026-10-13"
    assert salida["secciones"][1]["sin_informacion"] is True


def test_resumen_puro_no_resalta_dias_no_seguidos():
    from datetime import date

    datos = {"sintomas": [{"sintoma": "Fiebre", "intensidad": 5, "fecha": date(2026, 10, d)} for d in (1, 3, 5)]}
    salida = construir_resumen(["sintomas"], datos)
    assert not any(linea["destacado"] for linea in salida["secciones"][0]["lineas"])
