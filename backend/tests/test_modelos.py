"""Pruebas de integración: cifrado en BD y tablas de solo adición."""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models import Auditoria, Perfil, SintomaRegistro, Usuario


def crear_perfil(sesion: Session, nombre: str = "María Pérez") -> Perfil:
    usuario = Usuario(id=uuid.uuid4(), correo=f"{uuid.uuid4()}@ejemplo.co", hash_contrasena="hash-prueba")
    sesion.add(usuario)
    sesion.flush()  # el usuario debe existir antes que el perfil que lo referencia
    perfil = Perfil(
        id=uuid.uuid4(),
        nombre=nombre,
        fecha_nacimiento=date(1980, 1, 1),
        titular_usuario_id=usuario.id,
    )
    sesion.add(perfil)
    sesion.commit()
    return perfil


def test_nombre_del_perfil_se_guarda_cifrado(session: Session) -> None:
    perfil = crear_perfil(session)
    crudo = session.execute(
        text("SELECT nombre FROM perfil WHERE id = :id"), {"id": perfil.id}
    ).scalar_one()
    assert "María" not in crudo
    assert crudo.startswith("v1:")

    session.expire_all()
    assert session.get(Perfil, perfil.id).nombre == "María Pérez"


def test_auditoria_no_admite_modificacion(session: Session) -> None:
    session.add(Auditoria(accion="ACCESO_PERFIL", fecha=datetime.now(timezone.utc)))
    session.commit()
    with pytest.raises(DBAPIError):
        session.execute(text("UPDATE auditoria SET accion = 'MANIPULADO'"))
    session.rollback()


def test_registro_de_sintomas_no_admite_borrado(session: Session) -> None:
    perfil = crear_perfil(session)
    sintoma = SintomaRegistro(
        id=uuid.uuid4(),
        perfil_id=perfil.id,
        sintoma="Dolor de cabeza",
        intensidad=4,
        fecha=datetime.now(timezone.utc),
    )
    session.add(sintoma)
    session.commit()
    with pytest.raises(DBAPIError):
        session.execute(text("DELETE FROM sintoma_registro WHERE id = :id"), {"id": sintoma.id})
    session.rollback()


def test_borrado_de_cuenta_autorizado_con_bandera(session: Session) -> None:
    perfil = crear_perfil(session)
    perfil_id = perfil.id  # tras commit el objeto queda expirado; se guarda el id antes
    session.add(
        SintomaRegistro(
            id=uuid.uuid4(),
            perfil_id=perfil_id,
            sintoma="Fiebre",
            intensidad=6,
            fecha=datetime.now(timezone.utc),
        )
    )
    session.commit()

    session.execute(text("SET LOCAL alentia.permitir_borrado = 'on'"))
    session.execute(text("DELETE FROM perfil WHERE id = :id"), {"id": perfil_id})
    session.commit()

    restantes = session.execute(
        text("SELECT count(*) FROM sintoma_registro WHERE perfil_id = :id"), {"id": perfil_id}
    ).scalar_one()
    assert restantes == 0


def test_intensidad_fuera_de_rango_se_rechaza(session: Session) -> None:
    perfil = crear_perfil(session)
    session.add(
        SintomaRegistro(
            id=uuid.uuid4(),
            perfil_id=perfil.id,
            sintoma="Mareo",
            intensidad=11,
            fecha=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
