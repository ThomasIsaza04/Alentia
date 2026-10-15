"""Pruebas de perfiles, zonas, accesos e invitaciones contra PostgreSQL real (paso 4, §9.6)."""
import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from app.core.tokens import crear_access_token
from app.db.base import ahora_utc
from app.db.session import get_db
from app.main import app
from app.models import AccesoPerfil, InvitacionPerfil, Usuario
from app.services.correo import remitente

BASE = "/api/v1"


@pytest.fixture
def cliente(session):
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def crear_usuario(session: Session, verificado: bool = True, correo: str | None = None) -> Usuario:
    usuario = Usuario(
        id=uuid.uuid4(),
        correo=correo or f"{uuid.uuid4().hex[:12]}@ejemplo.co",
        hash_contrasena="hash-prueba",
        verificado=verificado,
    )
    session.add(usuario)
    session.commit()
    otorgar_consentimientos(session, usuario)
    return usuario


def otorgar_consentimientos(session: Session, usuario: Usuario) -> None:
    """Pruebas: cuenta con todas las finalidades aceptadas en la versión vigente."""
    from app.core.consentimiento import FINALIDADES, HASH_POLITICA, VERSION
    from app.db.base import ahora_utc
    from app.models import Consentimiento

    for finalidad in FINALIDADES:
        session.add(
            Consentimiento(
                usuario_id=usuario.id, finalidad=finalidad, version=VERSION,
                hash_politica=HASH_POLITICA, aceptado=True, ocurrido_en=ahora_utc(),
            )
        )
    session.commit()


def cabecera(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(usuario.id)}"}


def crear_perfil_de(cliente: TestClient, titular: Usuario, nombre: str = "María Pérez") -> str:
    r = cliente.post(
        f"{BASE}/perfiles",
        json={"nombre": nombre, "fecha_nacimiento": "1980-01-01"},
        headers=cabecera(titular),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def dar_acceso(session: Session, usuario: Usuario, perfil_id: str, rol: str, alcance: str) -> AccesoPerfil:
    acceso = AccesoPerfil(
        usuario_id=usuario.id,
        perfil_id=uuid.UUID(perfil_id),
        rol=rol,
        alcance=alcance,
        estado="activo",
        inicio=ahora_utc(),
    )
    session.add(acceso)
    session.commit()
    return acceso


def token_de_invitacion(correo: str) -> str:
    mensaje = remitente.ultimo_para(correo)
    assert mensaje is not None, "No se envió la invitación"
    return re.search(r"token=([A-Za-z0-9_\-]+)", mensaje.cuerpo).group(1)


def invitar(cliente: TestClient, titular: Usuario, perfil_id: str, correo: str, alcance: str) -> None:
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/invitaciones",
        json={"correo": correo, "alcance": alcance},
        headers=cabecera(titular),
    )
    assert r.status_code == 202, r.text


def accesos_de(cliente: TestClient, titular: Usuario, perfil_id: str) -> list[dict]:
    r = cliente.get(f"{BASE}/perfiles/{perfil_id}/accesos", headers=cabecera(titular))
    assert r.status_code == 200, r.text
    return r.json()


# ---------- perfiles ----------

def test_crear_perfil_cifra_el_nombre(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)

    crudo = session.execute(
        text("SELECT nombre FROM perfil WHERE id = :id"), {"id": uuid.UUID(perfil_id)}
    ).scalar_one()
    assert "María" not in crudo
    assert crudo.startswith("v1:")

    r = cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabecera(titular))
    assert r.json()["nombre"] == "María Pérez"
    assert r.json()["rol"] == "titular"


def test_menor_no_puede_registrarse_como_titular(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    r = cliente.post(
        f"{BASE}/perfiles",
        json={"nombre": "Lucía", "fecha_nacimiento": "2015-01-01", "dependiente": False},
        headers=cabecera(titular),
    )
    assert r.status_code == 422


def test_menor_dependiente_queda_con_representante(cliente: TestClient, session: Session) -> None:
    representante = crear_usuario(session)
    r = cliente.post(
        f"{BASE}/perfiles",
        json={"nombre": "Lucía", "fecha_nacimiento": "2015-01-01", "dependiente": True},
        headers=cabecera(representante),
    )
    assert r.status_code == 201
    assert r.json()["dependiente"] is True
    assert r.json()["rol"] == "representante"


def test_cuenta_sin_verificar_no_crea_perfiles(cliente: TestClient, session: Session) -> None:
    sin_verificar = crear_usuario(session, verificado=False)
    r = cliente.post(
        f"{BASE}/perfiles",
        json={"nombre": "Ana", "fecha_nacimiento": "1980-01-01"},
        headers=cabecera(sin_verificar),
    )
    assert r.status_code == 403


def test_actualizar_fecha_a_menor_exige_representante(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.patch(
        f"{BASE}/perfiles/{perfil_id}",
        json={"fecha_nacimiento": "2015-01-01"},
        headers=cabecera(titular),
    )
    assert r.status_code == 422


def test_sin_acceso_responde_404_y_no_revela_el_perfil(cliente: TestClient, session: Session) -> None:
    dueno = crear_usuario(session)
    ajeno = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, dueno)
    zona = cliente.post(f"{BASE}/perfiles/{perfil_id}/zonas", json={"nombre": "Cardiología"}, headers=cabecera(dueno))
    zona_id = zona.json()["id"]

    cabeceras = cabecera(ajeno)
    respuestas = [
        cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabeceras),
        cliente.patch(f"{BASE}/perfiles/{perfil_id}", json={"nombre": "X"}, headers=cabeceras),
        cliente.get(f"{BASE}/perfiles/{perfil_id}/zonas", headers=cabeceras),
        cliente.post(f"{BASE}/perfiles/{perfil_id}/zonas", json={"nombre": "X"}, headers=cabeceras),
        cliente.patch(f"{BASE}/zonas/{zona_id}", json={"archivada": True}, headers=cabeceras),
        cliente.get(f"{BASE}/perfiles/{perfil_id}/accesos", headers=cabeceras),
    ]
    assert all(r.status_code == 404 for r in respuestas)


def test_lector_consulta_pero_no_edita(cliente: TestClient, session: Session) -> None:
    dueno = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, dueno)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    cabeceras = cabecera(lector)

    assert cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabeceras).status_code == 200
    assert cliente.patch(f"{BASE}/perfiles/{perfil_id}", json={"nombre": "X"}, headers=cabeceras).status_code == 403
    assert cliente.post(f"{BASE}/perfiles/{perfil_id}/zonas", json={"nombre": "X"}, headers=cabeceras).status_code == 403
    assert cliente.get(f"{BASE}/perfiles/{perfil_id}/accesos", headers=cabeceras).status_code == 403


# ---------- zonas ----------

def test_zona_se_guarda_cifrada(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/zonas", json={"nombre": "Salud mental"}, headers=cabecera(titular))
    assert r.status_code == 201
    zona_id = r.json()["id"]

    crudo = session.execute(
        text("SELECT nombre FROM zona_consulta WHERE id = :id"), {"id": uuid.UUID(zona_id)}
    ).scalar_one()
    assert "Salud" not in crudo
    assert crudo.startswith("v1:")
    assert cliente.get(f"{BASE}/perfiles/{perfil_id}/zonas", headers=cabecera(titular)).json()[0]["nombre"] == "Salud mental"


def test_zona_archivada_se_oculta_salvo_que_se_pida(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    zona_id = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/zonas", json={"nombre": "Cardiología"}, headers=cabecera(titular)
    ).json()["id"]
    r = cliente.patch(f"{BASE}/zonas/{zona_id}", json={"archivada": True}, headers=cabecera(titular))
    assert r.status_code == 200

    assert cliente.get(f"{BASE}/perfiles/{perfil_id}/zonas", headers=cabecera(titular)).json() == []
    todas = cliente.get(
        f"{BASE}/perfiles/{perfil_id}/zonas?incluir_archivadas=true", headers=cabecera(titular)
    ).json()
    assert len(todas) == 1 and todas[0]["archivada"] is True


# ---------- invitaciones ----------

def test_flujo_de_invitacion_completo(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    correo_invitado = f"{uuid.uuid4().hex[:12]}@ejemplo.co"
    invitado = crear_usuario(session, correo=correo_invitado)
    perfil_id = crear_perfil_de(cliente, titular)

    invitar(cliente, titular, perfil_id, correo_invitado, "editor")
    token = token_de_invitacion(correo_invitado)

    r = cliente.post(f"{BASE}/invitaciones/aceptar", json={"token": token}, headers=cabecera(invitado))
    assert r.status_code == 200

    consulta = cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabecera(invitado))
    assert consulta.status_code == 200
    assert consulta.json()["alcance"] == "editor"
    assert consulta.json()["rol"] == "cuidador"
    assert cliente.patch(f"{BASE}/perfiles/{perfil_id}", json={"nombre": "Ana"}, headers=cabecera(invitado)).status_code == 200


def test_invitacion_no_se_reutiliza_ni_sirve_a_otra_cuenta(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    correo_invitado = f"{uuid.uuid4().hex[:12]}@ejemplo.co"
    invitado = crear_usuario(session, correo=correo_invitado)
    otra = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    invitar(cliente, titular, perfil_id, correo_invitado, "lector")
    token = token_de_invitacion(correo_invitado)

    assert cliente.post(f"{BASE}/invitaciones/aceptar", json={"token": token}, headers=cabecera(otra)).status_code == 400
    assert cliente.post(f"{BASE}/invitaciones/aceptar", json={"token": token}, headers=cabecera(invitado)).status_code == 200
    assert cliente.post(f"{BASE}/invitaciones/aceptar", json={"token": token}, headers=cabecera(invitado)).status_code == 400


def test_invitacion_vencida_se_rechaza(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    correo_invitado = f"{uuid.uuid4().hex[:12]}@ejemplo.co"
    invitado = crear_usuario(session, correo=correo_invitado)
    perfil_id = crear_perfil_de(cliente, titular)
    invitar(cliente, titular, perfil_id, correo_invitado, "lector")
    token = token_de_invitacion(correo_invitado)

    session.execute(
        update(InvitacionPerfil)
        .where(InvitacionPerfil.correo_invitado == correo_invitado)
        .values(vence_en=ahora_utc() - timedelta(minutes=1))
    )
    session.commit()
    assert cliente.post(f"{BASE}/invitaciones/aceptar", json={"token": token}, headers=cabecera(invitado)).status_code == 400


def test_no_se_puede_invitar_a_uno_mismo(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/invitaciones",
        json={"correo": titular.correo, "alcance": "lector"},
        headers=cabecera(titular),
    )
    assert r.status_code == 422


# ---------- revocación ----------

def test_revocar_acceso_aplica_en_la_siguiente_peticion(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    acceso_id = next(a["id"] for a in accesos_de(cliente, titular, perfil_id) if a["usuario_id"] == str(lector.id))

    assert cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabecera(lector)).status_code == 200
    r = cliente.delete(f"{BASE}/perfiles/{perfil_id}/accesos/{acceso_id}", headers=cabecera(titular))
    assert r.status_code == 200
    assert cliente.get(f"{BASE}/perfiles/{perfil_id}", headers=cabecera(lector)).status_code == 404


def test_el_titular_no_puede_retirar_su_acceso(cliente: TestClient, session: Session) -> None:
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    acceso_titular = next(a["id"] for a in accesos_de(cliente, titular, perfil_id) if a["rol"] == "titular")
    r = cliente.delete(f"{BASE}/perfiles/{perfil_id}/accesos/{acceso_titular}", headers=cabecera(titular))
    assert r.status_code == 422


def test_menor_conserva_al_menos_un_representante(cliente: TestClient, session: Session) -> None:
    rep_a = crear_usuario(session)
    rep_b = crear_usuario(session)
    r = cliente.post(
        f"{BASE}/perfiles",
        json={"nombre": "Lucía", "fecha_nacimiento": "2015-01-01", "dependiente": True},
        headers=cabecera(rep_a),
    )
    perfil_id = r.json()["id"]
    acceso_b = dar_acceso(session, rep_b, perfil_id, rol="representante", alcance="admin")

    # Con dos representantes, uno puede salir.
    acceso_a = next(a["id"] for a in accesos_de(cliente, rep_a, perfil_id) if a["usuario_id"] == str(rep_a.id))
    assert cliente.delete(f"{BASE}/perfiles/{perfil_id}/accesos/{acceso_a}", headers=cabecera(rep_b)).status_code == 200

    # Con uno solo, no puede quedarse sin representante.
    assert (
        cliente.delete(f"{BASE}/perfiles/{perfil_id}/accesos/{acceso_b.id}", headers=cabecera(rep_b)).status_code
        == 422
    )
