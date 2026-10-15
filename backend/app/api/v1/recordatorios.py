"""Recordatorios dentro de la app y calendario .ics (paso 9, RF-NOT-02 y RF-NOT-03)."""
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import usuario_verificado
from app.core.config import settings
from app.db.base import ahora_utc
from app.db.session import get_db
from app.models import Medicamento, TomaProgramada, Usuario
from app.services import consentimiento as consentimientos
from app.services import salud as salud_svc
from app.services import calendario
from app.services.tareas import pendientes_del_usuario

router = APIRouter(tags=["recordatorios"], prefix="/api/v1")


@router.get("/recordatorios")
def recordatorios(
    zona_horaria: str | None = Query(default=None, max_length=60),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> dict:
    zona = zona_horaria or settings.zona_horaria_por_defecto
    return {
        "aviso": calendario.AVISO,
        "items": pendientes_del_usuario(db, usuario, zona, ahora_utc()),
    }


@router.get("/perfiles/{perfil_id}/calendario.ics")
def calendario_ics(
    perfil_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> Response:
    salud_svc.acceso_a(db, usuario, perfil_id, "lector")
    consentimientos.exigir(db, usuario, "notificaciones")
    ahora = ahora_utc()
    from datetime import timedelta

    filas = db.execute(
        select(TomaProgramada, Medicamento)
        .join(Medicamento, Medicamento.id == TomaProgramada.medicamento_id)
        .where(
            Medicamento.perfil_id == perfil_id,
            Medicamento.activo.is_(True),
            TomaProgramada.programada_en >= ahora - timedelta(days=1),
        )
        .order_by(TomaProgramada.programada_en)
    ).all()
    tomas = [(str(t.id), m.nombre, m.dosis, t.programada_en) for t, m in filas]
    contenido = calendario.generar(tomas, ahora)
    return Response(
        contenido,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="alentia-tomas.ics"',
            "Cache-Control": "no-store",
        },
    )
