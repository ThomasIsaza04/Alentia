"""Tareas de mantenimiento de recordatorios (paso 9). Se ejecutan con `python -m app.tareas.ejecutar`.

- extender_tomas: programa 30 días hacia adelante para pautas activas que se acercan a su último día programado.
- marcar_omitidas: registra "omitida" (sin usuario que la confirme) las tomas que pasaron el plazo de omisión.
- Las cuentas vencidas se eliminan con eliminar_vencidas (paso 8).
"""
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import ahora_utc
from app.models import AccesoPerfil, Medicamento, TomaProgramada, TomaRegistro, Usuario
from app.services import consentimiento as consentimientos
from app.services.perfiles import _vigente
from app.services.salud import DIAS_DE_PROGRAMACION, programar_tomas, zona_valida

UMBRAL_EXTENSION_DIAS = 14


def extender_tomas(db: Session, ahora: datetime) -> int:
    total = 0
    for m in db.scalars(select(Medicamento).where(Medicamento.activo.is_(True))):
        ultima = db.scalar(select(func.max(TomaProgramada.programada_en)).where(TomaProgramada.medicamento_id == m.id))
        if ultima is None or ultima >= ahora + timedelta(days=UMBRAL_EXTENSION_DIAS):
            continue
        zona = zona_valida(m.zona_horaria)
        inicio = ultima.astimezone(zona).date() + timedelta(days=1)
        tope = ahora.astimezone(zona).date() + timedelta(days=DIAS_DE_PROGRAMACION - 1)
        fin = m.fin.astimezone(zona).date() if m.fin else None
        fin_efectivo = tope if fin is None else min(fin, tope)
        if inicio > fin_efectivo:
            continue
        total += programar_tomas(db, m, zona, json.loads(m.frecuencia), inicio, fin_efectivo)
    db.commit()
    return total


def marcar_omitidas(db: Session, ahora: datetime) -> int:
    limite = ahora - timedelta(hours=settings.horas_para_omision)
    pendientes = db.scalars(
        select(TomaProgramada)
        .join(Medicamento, Medicamento.id == TomaProgramada.medicamento_id)
        .where(
            Medicamento.activo.is_(True),
            TomaProgramada.programada_en < limite,
            ~exists().where(TomaRegistro.toma_programada_id == TomaProgramada.id),
        )
    ).all()
    for toma in pendientes:
        db.add(
            TomaRegistro(
                id=uuid.uuid4(),
                toma_programada_id=toma.id,
                estado="omitida",
                registrada_en=ahora,
                registrada_por=None,
            )
        )
    db.commit()
    return len(pendientes)


def ejecutar_todas(db: Session, ahora: datetime | None = None) -> dict[str, int]:
    from app.services.cuenta import eliminar_vencidas

    ahora = ahora or ahora_utc()
    return {
        "tomas_extendidas": extender_tomas(db, ahora),
        "tomas_omitidas": marcar_omitidas(db, ahora),
        "cuentas_eliminadas": eliminar_vencidas(db, ahora),
    }


def estado_atraso(programada_en: datetime, registro_estado: str | None, ahora: datetime) -> str | None:
    """Estado mostrado en la lista de tomas. 'atrasada' es calculado; 'omitida' se persiste con marcar_omitidas."""
    if registro_estado is not None:
        return registro_estado
    if ahora > programada_en + timedelta(hours=settings.ventana_atraso_horas):
        return "atrasada"
    return None


def pendientes_del_usuario(db: Session, usuario: Usuario, zona_nombre: str, ahora: datetime) -> list[dict]:
    """Tomas que requieren atención ahora: vencidas dentro de la ventana de omisión, o próximas en 15 minutos."""
    consentimientos.exigir(db, usuario, "notificaciones")
    zona = zona_valida(zona_nombre)
    desde = ahora - timedelta(hours=settings.horas_para_omision)
    hasta = ahora + timedelta(minutes=15)
    filas = db.execute(
        select(TomaProgramada, Medicamento)
        .join(Medicamento, Medicamento.id == TomaProgramada.medicamento_id)
        .join(AccesoPerfil, AccesoPerfil.perfil_id == Medicamento.perfil_id)
        .where(
            AccesoPerfil.usuario_id == usuario.id,
            AccesoPerfil.alcance.in_(("editor", "admin")),
            _vigente(),
            Medicamento.activo.is_(True),
            TomaProgramada.programada_en >= desde,
            TomaProgramada.programada_en <= hasta,
        )
        .order_by(TomaProgramada.programada_en)
    ).all()
    salida = []
    for toma, med in filas:
        ultimo = db.scalar(
            select(TomaRegistro.estado)
            .where(TomaRegistro.toma_programada_id == toma.id)
            .order_by(TomaRegistro.registrada_en.desc())
            .limit(1)
        )
        if ultimo is not None:
            continue
        salida.append(
            {
                "toma_id": str(toma.id),
                "perfil_id": str(med.perfil_id),
                "nombre": med.nombre,
                "dosis": med.dosis,
                "hora_local": toma.programada_en.astimezone(zona).strftime("%H:%M"),
                "fecha_local": toma.programada_en.astimezone(zona).date().isoformat(),
                "estado": estado_atraso(toma.programada_en, None, ahora),
            }
        )
    return salida

