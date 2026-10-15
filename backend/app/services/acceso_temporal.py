"""Acceso temporal del profesional (paso 7, RF-QRM-01 a RF-QRM-05).

Ciclo de vida de un acceso: pendiente -> consumido (PIN correcto, una sola vez).
Sale de 'pendiente' por revocación, bloqueo (5 PIN incorrectos) o vencimiento.
La sesión del profesional nunca dura más que el acceso que la originó.
"""
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errores import PinIncorrecto, RecursoNoEncontrado, ReglaNegocio, SesionInvalida
from app.core.passwords import hashear, verificar
from app.core.tokens import hash_token, token_aleatorio
from app.db.base import ahora_utc
from app.models import Auditoria, AccesoTemporal, EventoAccesoTemporal, SesionAccesoTemporal, Usuario
from app.services import consentimiento as consentimientos
from app.services.perfiles import acceso_a

CATEGORIAS = ("diagnosticos", "medicamentos", "sintomas")
DURACIONES = (15, 30)
MAX_INTENTOS_PIN = 5
MINUTOS_SESION = 15


def _no_disponible() -> RecursoNoEncontrado:
    # Mensaje genérico: no revela si el enlace existió, venció, se usó o fue revocado.
    return RecursoNoEncontrado("Este acceso no está disponible")


def estado_de(acceso: AccesoTemporal, ahora: datetime) -> str:
    if acceso.revocado_en is not None:
        return "revocado"
    if acceso.bloqueado_en is not None:
        return "bloqueado"
    if acceso.consumido_en is not None:
        return "consumido"
    if ahora >= acceso.vence_en:
        return "expirado"
    return "pendiente"


def _evento(db: Session, acceso_id: uuid.UUID, tipo: str, dispositivo: str) -> None:
    db.add(
        EventoAccesoTemporal(
            acceso_id=acceso_id,
            tipo=tipo,
            ocurrido_en=ahora_utc(),
            tipo_dispositivo=dispositivo,
        )
    )


def _pin() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def _categorias_validas(categorias: list[str]) -> str:
    unicas = sorted(set(categorias))
    if not unicas:
        raise ReglaNegocio("Elige al menos una categoría para compartir")
    if any(c not in CATEGORIAS for c in unicas):
        raise ReglaNegocio("Hay una categoría no válida")
    return ",".join(unicas)


# ---------- titular ----------

def crear(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, categorias: list[str], duracion: int, dispositivo: str
) -> tuple[AccesoTemporal, str, str]:
    acceso_a(db, usuario, perfil_id, "editor")
    consentimientos.exigir(db, usuario, "qr")
    if duracion not in DURACIONES:
        raise ReglaNegocio("La duración debe ser de 15 o 30 minutos")
    cadena = _categorias_validas(categorias)
    token = token_aleatorio()
    pin = _pin()
    acceso = AccesoTemporal(
        perfil_id=perfil_id,
        creado_por=usuario.id,
        categorias=cadena,
        duracion_minutos=duracion,
        hash_token=hash_token(token),
        hash_pin=hashear(pin),
        vence_en=ahora_utc() + timedelta(minutes=duracion),
    )
    db.add(acceso)
    db.flush()
    _evento(db, acceso.id, "generado", dispositivo)
    db.add(Auditoria(accion="ACCESO_TEMPORAL_CREADO", actor_usuario_id=usuario.id, perfil_id=perfil_id, fecha=ahora_utc()))
    db.commit()
    return acceso, token, pin


def listar(db: Session, usuario: Usuario, perfil_id: uuid.UUID) -> list[AccesoTemporal]:
    acceso_a(db, usuario, perfil_id, "editor")
    return list(
        db.scalars(
            select(AccesoTemporal)
            .where(AccesoTemporal.perfil_id == perfil_id)
            .order_by(AccesoTemporal.creado_en.desc())
        )
    )


def _acceso_del_titular(db: Session, usuario: Usuario, acceso_id: uuid.UUID) -> AccesoTemporal:
    acceso = db.get(AccesoTemporal, acceso_id)
    if acceso is None:
        raise RecursoNoEncontrado("Acceso no encontrado")
    acceso_a(db, usuario, acceso.perfil_id, "editor")
    return acceso


def bitacora(db: Session, usuario: Usuario, acceso_id: uuid.UUID) -> list[EventoAccesoTemporal]:
    acceso = _acceso_del_titular(db, usuario, acceso_id)
    return list(
        db.scalars(
            select(EventoAccesoTemporal)
            .where(EventoAccesoTemporal.acceso_id == acceso.id)
            .order_by(EventoAccesoTemporal.ocurrido_en)
        )
    )


def revocar(db: Session, usuario: Usuario, acceso_id: uuid.UUID, dispositivo: str) -> AccesoTemporal:
    acceso = _acceso_del_titular(db, usuario, acceso_id)
    if acceso.revocado_en is None:
        acceso.revocado_en = ahora_utc()
        _evento(db, acceso.id, "revocado", dispositivo)
        db.add(Auditoria(accion="ACCESO_TEMPORAL_REVOCADO", actor_usuario_id=usuario.id, perfil_id=acceso.perfil_id, fecha=ahora_utc()))
        db.commit()
    return acceso


# ---------- profesional (sin cuenta) ----------

def _por_token(db: Session, token: str) -> AccesoTemporal | None:
    return db.scalar(select(AccesoTemporal).where(AccesoTemporal.hash_token == hash_token(token)))


def abrir(db: Session, token: str, dispositivo: str) -> AccesoTemporal:
    acceso = _por_token(db, token)
    if acceso is None or estado_de(acceso, ahora_utc()) != "pendiente":
        raise _no_disponible()
    _evento(db, acceso.id, "abierto", dispositivo)
    db.commit()
    return acceso


def verificar_pin(db: Session, token: str, pin: str, dispositivo: str) -> tuple[str, datetime]:
    ahora = ahora_utc()
    acceso = _por_token(db, token)
    if acceso is None or estado_de(acceso, ahora) != "pendiente":
        raise _no_disponible()

    if not verificar(pin, acceso.hash_pin):
        acceso.intentos_fallidos += 1
        _evento(db, acceso.id, "pin_fallido", dispositivo)
        if acceso.intentos_fallidos >= MAX_INTENTOS_PIN:
            acceso.bloqueado_en = ahora
            _evento(db, acceso.id, "bloqueado", dispositivo)
        db.commit()
        if acceso.bloqueado_en is not None:
            raise _no_disponible()
        restantes = MAX_INTENTOS_PIN - acceso.intentos_fallidos
        raise PinIncorrecto(f"El PIN no es correcto. Te quedan {restantes} intentos")

    acceso.consumido_en = ahora
    _evento(db, acceso.id, "consumido", dispositivo)
    token_sesion = token_aleatorio()
    vence = min(ahora + timedelta(minutes=MINUTOS_SESION), acceso.vence_en)
    db.add(
        SesionAccesoTemporal(
            acceso_id=acceso.id,
            hash_token=hash_token(token_sesion),
            creada_en=ahora,
            vence_en=vence,
        )
    )
    db.commit()
    return token_sesion, vence


def acceso_de_sesion(db: Session, token_sesion: str) -> AccesoTemporal:
    sesion = db.scalar(
        select(SesionAccesoTemporal).where(SesionAccesoTemporal.hash_token == hash_token(token_sesion))
    )
    ahora = ahora_utc()
    if sesion is None or ahora >= sesion.vence_en:
        raise SesionInvalida("La sesión expiró. Pide un nuevo código al paciente")
    acceso = db.get(AccesoTemporal, sesion.acceso_id)
    if acceso is None or acceso.revocado_en is not None or acceso.bloqueado_en is not None:
        raise SesionInvalida("El paciente revocó este acceso")
    return acceso
