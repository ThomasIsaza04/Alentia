"""Consentimiento por finalidad (RF-CON-01 y RF-CON-02)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.consentimiento import FINALIDADES, HASH_POLITICA, OBLIGATORIA, TEXTOS, VERSION
from app.core.errores import ConsentimientoRequerido, ReglaNegocio
from app.db.base import ahora_utc
from app.models import Auditoria, Consentimiento, Usuario


def _ultimos(db: Session, usuario_id: uuid.UUID) -> dict[str, Consentimiento]:
    ultimos: dict[str, Consentimiento] = {}
    filas = db.scalars(
        select(Consentimiento)
        .where(Consentimiento.usuario_id == usuario_id)
        .order_by(Consentimiento.ocurrido_en.desc())
    )
    for fila in filas:
        ultimos.setdefault(fila.finalidad, fila)
    return ultimos


def estado(db: Session, usuario: Usuario) -> dict[str, dict]:
    ultimos = _ultimos(db, usuario.id)
    salida = {}
    for finalidad in FINALIDADES:
        fila = ultimos.get(finalidad)
        vigente = bool(fila and fila.aceptado and fila.version == VERSION)
        salida[finalidad] = {
            "aceptado": vigente,
            "version_aceptada": fila.version if fila and fila.aceptado else None,
        }
    return salida


def politica() -> dict:
    return {"version": VERSION, "hash": HASH_POLITICA, "textos": TEXTOS, "obligatoria": OBLIGATORIA}


def exigir(db: Session, usuario: Usuario, finalidad: str) -> None:
    """Se llama antes de guardar datos que dependen de la finalidad."""
    fila = _ultimos(db, usuario.id).get(finalidad)
    if not (fila and fila.aceptado and fila.version == VERSION):
        if finalidad == OBLIGATORIA:
            mensaje = "Acepta la política de tratamiento de datos de salud para continuar"
        elif finalidad == "qr":
            mensaje = "Acepta el consentimiento de accesos temporales para generar un QR"
        else:
            mensaje = "Acepta el consentimiento de notificaciones para continuar"
        raise ConsentimientoRequerido(mensaje)


def registrar(db: Session, usuario: Usuario, finalidad: str, version: str, aceptado: bool) -> dict[str, dict]:
    if finalidad not in FINALIDADES:
        raise ReglaNegocio("La finalidad no es válida")
    if version != VERSION:
        raise ReglaNegocio("La política cambió. Revisa la versión vigente antes de aceptar")
    if finalidad == OBLIGATORIA and not aceptado:
        raise ReglaNegocio("Para retirar el consentimiento de salud, elimina tu cuenta")
    db.add(
        Consentimiento(
            usuario_id=usuario.id,
            finalidad=finalidad,
            version=VERSION,
            hash_politica=HASH_POLITICA,
            aceptado=aceptado,
            ocurrido_en=ahora_utc(),
        )
    )
    db.add(
        Auditoria(
            accion="CONSENTIMIENTO_ACEPTADO" if aceptado else "CONSENTIMIENTO_RETIRADO",
            actor_usuario_id=usuario.id,
            perfil_id=None,
            fecha=ahora_utc(),
        )
    )
    db.commit()
    return estado(db, usuario)


def historial(db: Session, usuario: Usuario) -> list[Consentimiento]:
    return list(
        db.scalars(
            select(Consentimiento)
            .where(Consentimiento.usuario_id == usuario.id)
            .order_by(Consentimiento.ocurrido_en)
        )
    )
