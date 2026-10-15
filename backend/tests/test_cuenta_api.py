"""Pruebas de consentimiento, exportación, eliminación y corrección (paso 8) contra PostgreSQL real."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core import passwords
from app.core.consentimiento import VERSION
from app.db.session import get_db
from app.main import app
from app.models import (
    AccesoPerfil,
    Auditoria,
    Consentimiento,
    Medicamento,
    Perfil,
    SintomaRegistro,
    Usuario,
)
from app.services.cuenta import eliminar_vencidas
from tests.test_perfiles_api import BASE, cabecera, crear_perfil_de, crear_usuario, dar_acceso

CLAVE = "Clave-segura-2026"
PAGINA = {"desde": "2026-10-01", "hasta": "2026-10-01", "zona_horaria": "America/Bogota"}


@pytest.fixture
def cliente(session):
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def con_clave(session: Session, usuario: Usuario) -> Usuario:
    usuario.hash_contrasena = passwords.hashear(CLAVE)
    session.commit()
    return usuario


def usuario_sin_consentimientos(session: Session) -> Usuario:
    """El consentimiento es solo adición: en lugar de borrar filas, se crea una cuenta sin ninguna."""
    usuario = Usuario(id=uuid.uuid4(), correo=f"{uuid.uuid4().hex[:12]}@ejemplo.co",
                      hash_contrasena="hash-prueba", verificado=True)
    session.add(usuario)
    session.commit()
    return usuario


def _medicamento(cliente, titular, perfil_id):
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/medicamentos",
        json={"nombre": "Losartán", "dosis": "50 mg", "frecuencia": {"tipo": "horarios", "horas": ["08:00"]},
              "inicio": "2026-10-01", "zona_horaria": "America/Bogota"},
        headers=cabecera(titular),
    )
    return r


# ---------- consentimiento ----------

def test_sin_consentimiento_de_salud_no_se_guardan_datos(cliente, session):
    titular = usuario_sin_consentimientos(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = _medicamento(cliente, titular, perfil_id)
    assert r.status_code == 403
    assert r.json()["title"] == "Consentimiento requerido"


def test_aceptar_salud_permite_guardar_y_la_politica_se_expone(cliente, session):
    titular = usuario_sin_consentimientos(session)
    perfil_id = crear_perfil_de(cliente, titular)

    pol = cliente.get(f"{BASE}/cuenta/consentimientos", headers=cabecera(titular)).json()
    assert pol["politica"]["version"] == VERSION
    assert len(pol["politica"]["hash"]) == 64
    assert set(pol["politica"]["textos"]) == {"salud", "notificaciones", "qr"}
    assert pol["estado"]["salud"]["aceptado"] is False

    r = cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "salud", "version": VERSION, "aceptado": True},
                     headers=cabecera(titular))
    assert r.status_code == 200 and r.json()["estado"]["salud"]["aceptado"] is True
    assert _medicamento(cliente, titular, perfil_id).status_code == 201


def test_version_antigua_no_se_acepta(cliente, session):
    titular = crear_usuario(session)
    r = cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "salud", "version": "2020-01-v0", "aceptado": True},
                     headers=cabecera(titular))
    assert r.status_code == 422


def test_salud_no_se_puede_retirar_sin_eliminar_la_cuenta(cliente, session):
    titular = crear_usuario(session)
    r = cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "salud", "version": VERSION, "aceptado": False},
                     headers=cabecera(titular))
    assert r.status_code == 422


def test_retirar_qr_bloquea_nuevos_accesos_y_volver_a_aceptar_los_reabre(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    cuerpo_acceso = {"categorias": ["medicamentos"], "duracion_minutos": 15}
    cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "qr", "version": VERSION, "aceptado": False},
                 headers=cabecera(titular))
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/accesos-temporales", json=cuerpo_acceso, headers=cabecera(titular))
    assert r.status_code == 403
    cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "qr", "version": VERSION, "aceptado": True},
                 headers=cabecera(titular))
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/accesos-temporales", json=cuerpo_acceso, headers=cabecera(titular))
    assert r.status_code == 201


def test_el_historial_de_consentimientos_no_se_borra(cliente, session):
    titular = crear_usuario(session)
    cliente.post(f"{BASE}/cuenta/consentimientos", json={"finalidad": "notificaciones", "version": VERSION, "aceptado": False},
                 headers=cabecera(titular))
    filas = session.scalar(select(func.count()).select_from(Consentimiento).where(Consentimiento.usuario_id == titular.id,
                                                                                 Consentimiento.finalidad == "notificaciones"))
    # Dos filas: la aceptación automática del alta de prueba y el retiro. Ninguna se borra.
    assert filas == 2


# ---------- exportación ----------

def test_exportacion_json_incluye_datos_y_no_incluye_secretos(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular, nombre="Mónica Ortiz")
    _medicamento(cliente, titular, perfil_id)
    cliente.post(f"{BASE}/perfiles/{perfil_id}/accesos-temporales",
                 json={"categorias": ["medicamentos"], "duracion_minutos": 15}, headers=cabecera(titular))

    r = cliente.get(f"{BASE}/cuenta/exportacion?formato=json", headers=cabecera(titular))
    assert r.status_code == 200
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.headers["Cache-Control"] == "no-store"
    cuerpo = r.json()
    assert cuerpo["cuenta"]["correo"] == titular.correo
    perfil = next(p for p in cuerpo["perfiles"] if p["nombre"] == "Mónica Ortiz")
    assert perfil["medicamentos"][0]["nombre"] == "Losartán"
    assert len(perfil["medicamentos"][0]["tomas"]) == 30
    assert perfil["accesos_temporales"][0]["estado"] == "pendiente"
    texto = r.text
    assert "hash_token" not in texto and "hash_pin" not in texto and "pin" not in perfil["accesos_temporales"][0]


def test_exportacion_csv_tiene_cabecera_y_filas(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    r = cliente.get(f"{BASE}/cuenta/exportacion?formato=csv", headers=cabecera(titular))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "seccion,perfil,fecha,detalle,estado"
    assert any(linea.startswith("medicamento,") for linea in lineas)


def test_exportacion_no_incluye_perfiles_de_otros(cliente, session):
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_ajeno = crear_perfil_de(cliente, titular, nombre="Perfil ajeno")
    dar_acceso(session, lector, perfil_ajeno, rol="cuidador", alcance="lector")
    crear_perfil_de(cliente, lector, nombre="Mi perfil")
    cuerpo = cliente.get(f"{BASE}/cuenta/exportacion?formato=json", headers=cabecera(lector)).json()
    nombres = [p["nombre"] for p in cuerpo["perfiles"]]
    assert nombres == ["Mi perfil"]


# ---------- eliminación ----------

def test_eliminacion_exige_la_clave_y_tiene_periodo_de_gracia(cliente, session):
    usuario = con_clave(session, crear_usuario(session))
    r = cliente.post(f"{BASE}/cuenta/eliminacion", json={"clave": "otra-clave"}, headers=cabecera(usuario))
    assert r.status_code == 403

    r = cliente.post(f"{BASE}/cuenta/eliminacion", json={"clave": CLAVE}, headers=cabecera(usuario))
    assert r.status_code == 200
    eliminar_en = datetime.fromisoformat(r.json()["eliminar_en"])
    dias = (eliminar_en - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 6.9 < dias <= 7.0

    estado = cliente.get(f"{BASE}/cuenta/eliminacion", headers=cabecera(usuario)).json()
    assert estado["eliminar_en"] is not None


def test_cancelar_la_eliminacion_dentro_del_plazo(cliente, session):
    usuario = con_clave(session, crear_usuario(session))
    cliente.post(f"{BASE}/cuenta/eliminacion", json={"clave": CLAVE}, headers=cabecera(usuario))
    r = cliente.post(f"{BASE}/cuenta/eliminacion/cancelar", headers=cabecera(usuario))
    assert r.status_code == 200 and r.json()["eliminar_en"] is None


def test_purga_antes_del_plazo_no_borra_nada(session):
    usuario = con_clave(session, crear_usuario(session))
    usuario.eliminar_en = datetime.now(timezone.utc) + timedelta(days=3)
    session.commit()
    assert eliminar_vencidas(session, datetime.now(timezone.utc)) == 0
    assert session.get(Usuario, usuario.id) is not None


def test_purga_vencida_borra_perfiles_registros_y_accesos_de_terceros(cliente, session):
    titular = con_clave(session, crear_usuario(session))
    otro = crear_usuario(session)
    perfil_propio = crear_perfil_de(cliente, titular, nombre="Propio")
    _medicamento(cliente, titular, perfil_propio)
    cliente.post(f"{BASE}/perfiles/{perfil_propio}/sintomas",
                 json={"sintoma": "Mareo", "intensidad": 3, "fecha": "2026-10-01T10:00:00-05:00"},
                 headers=cabecera(titular))
    med_id = session.scalar(select(Medicamento.id).where(Medicamento.perfil_id == uuid.UUID(perfil_propio)))

    perfil_de_otro = crear_perfil_de(cliente, otro, nombre="Del otro")
    dar_acceso(session, titular, perfil_de_otro, rol="cuidador", alcance="lector")
    perfil_otro_del_titular = crear_perfil_de(cliente, otro, nombre="Compartido")
    dar_acceso(session, titular, perfil_otro_del_titular, rol="cuidador", alcance="editor")

    titular.eliminar_en = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()
    titular_id = titular.id

    assert eliminar_vencidas(session, datetime.now(timezone.utc)) == 1
    session.expire_all()

    assert session.get(Usuario, titular_id) is None
    assert session.get(Perfil, uuid.UUID(perfil_propio)) is None
    assert session.scalar(select(func.count()).select_from(Medicamento).where(Medicamento.id == med_id)) == 0
    assert session.scalar(select(func.count()).select_from(SintomaRegistro).where(SintomaRegistro.perfil_id == uuid.UUID(perfil_propio))) == 0
    assert session.scalar(select(func.count()).select_from(AccesoPerfil).where(AccesoPerfil.usuario_id == titular_id)) == 0
    assert session.get(Perfil, uuid.UUID(perfil_de_otro)) is not None
    assert session.get(Usuario, otro.id) is not None
    ultima = session.scalar(select(Auditoria).where(Auditoria.accion == "CUENTA_ELIMINADA").order_by(Auditoria.id.desc()).limit(1))
    assert ultima is not None and ultima.actor_usuario_id is None and ultima.perfil_id is None


# ---------- corrección de datos ----------

def test_corregir_nombre_y_dosis_de_medicamento_y_descripcion_de_diagnostico(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id).json()
    r = cliente.patch(f"{BASE}/medicamentos/{med['id']}", json={"nombre": "Losartán potásico", "dosis": "100 mg"},
                      headers=cabecera(titular))
    assert r.status_code == 200
    assert r.json()["nombre"] == "Losartán potásico" and r.json()["dosis"] == "100 mg" and r.json()["activo"] is True
    crudo = session.execute(text("SELECT nombre FROM medicamento WHERE id = :id"), {"id": med["id"]}).scalar()
    assert crudo.startswith("v1:")

    diag = cliente.post(f"{BASE}/perfiles/{perfil_id}/diagnosticos",
                        json={"descripcion": "Hipertension", "fecha": "2026-09-20"}, headers=cabecera(titular)).json()
    r = cliente.patch(f"{BASE}/diagnosticos/{diag['id']}", json={"descripcion": "Hipertensión arterial"},
                      headers=cabecera(titular))
    assert r.status_code == 200 and r.json()["descripcion"] == "Hipertensión arterial" and r.json()["estado"] == "vigente"
