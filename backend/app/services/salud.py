"""Registros de salud (pasos 5 y 6): medicación con tomas programadas, registro de tomas,
síntomas y diagnósticos.

Reglas:
- Los horarios de la pauta se escriben en la zona horaria del cliente y se guardan en UTC.
- Las tomas se programan 30 días hacia adelante desde la fecha de inicio.
- Un registro de toma es de solo adición: una corrección es un registro nuevo y gana el más reciente.
- Todo acceso pasa por `acceso_a` (404 sin acceso, 403 si el alcance no alcanza).
"""
import json
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errores import RecursoNoEncontrado, ReglaNegocio
from app.db.base import ahora_utc
from app.models import (
    Auditoria,
    Diagnostico,
    Medicamento,
    SintomaRegistro,
    TomaProgramada,
    TomaRegistro,
    Usuario,
    ZonaConsulta,
)
from app.services import consentimiento as consentimientos
from app.services.perfiles import acceso_a

DIAS_DE_PROGRAMACION = 30
MAX_DIAS_CONSULTA = 62


def zona_valida(nombre: str) -> ZoneInfo:
    try:
        return ZoneInfo(nombre)
    except (ZoneInfoNotFoundError, ValueError):
        raise ReglaNegocio("La zona horaria no es válida")


def _auditar(db: Session, accion: str, actor: uuid.UUID, perfil_id: uuid.UUID | None) -> None:
    db.add(Auditoria(accion=accion, actor_usuario_id=actor, perfil_id=perfil_id, fecha=ahora_utc()))


def horas_del_dia(frecuencia: dict) -> list[time]:
    """Horas locales de un día según la pauta: horas fijas, o cada N horas desde una hora de inicio."""
    if frecuencia["tipo"] == "horarios":
        return sorted(time.fromisoformat(h) for h in frecuencia["horas"])
    desde = time.fromisoformat(frecuencia["desde"])
    minutos = desde.hour * 60 + desde.minute
    horas = []
    while minutos < 24 * 60:
        horas.append(time(minutos // 60, minutos % 60))
        minutos += frecuencia["cada_horas"] * 60
    return horas


def programar_tomas(
    db: Session, medicamento: Medicamento, zona: ZoneInfo, frecuencia: dict, inicio: date, fin: date | None
) -> int:
    ultimo = inicio + timedelta(days=DIAS_DE_PROGRAMACION - 1)
    if fin is not None and fin < ultimo:
        ultimo = fin
    filas = []
    dia = inicio
    while dia <= ultimo:
        for hora in horas_del_dia(frecuencia):
            local = datetime.combine(dia, hora, tzinfo=zona)
            filas.append(
                {
                    "id": uuid.uuid4(),
                    "medicamento_id": medicamento.id,
                    "programada_en": local.astimezone(timezone.utc),
                }
            )
        dia += timedelta(days=1)
    if filas:
        db.execute(
            insert(TomaProgramada.__table__)
            .on_conflict_do_nothing(constraint="uq_toma_medicamento_hora"),
            filas,
        )
    return len(filas)


# ---------- medicación ----------

def crear_medicamento(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, datos: dict
) -> Medicamento:
    acceso_a(db, usuario, perfil_id, "editor")
    consentimientos.exigir(db, usuario, "salud")
    zona = zona_valida(datos["zona_horaria"])
    fin = datos.get("fin")
    if fin is not None and fin < datos["inicio"]:
        raise ReglaNegocio("La fecha de fin no puede ser anterior al inicio")
    medicamento = Medicamento(
        perfil_id=perfil_id,
        nombre=datos["nombre"],
        dosis=datos["dosis"],
        frecuencia=json.dumps(datos["frecuencia"], ensure_ascii=False),
        inicio=datetime.combine(datos["inicio"], time(0), tzinfo=zona).astimezone(timezone.utc),
        fin=None if fin is None else datetime.combine(fin, time(23, 59), tzinfo=zona).astimezone(timezone.utc),
        activo=True,
        zona_horaria=datos["zona_horaria"],
    )
    db.add(medicamento)
    db.flush()
    programar_tomas(db, medicamento, zona, datos["frecuencia"], datos["inicio"], fin)
    _auditar(db, "MEDICAMENTO_CREADO", usuario.id, perfil_id)
    db.commit()
    return medicamento


def listar_medicamentos(db: Session, usuario: Usuario, perfil_id: uuid.UUID) -> list[Medicamento]:
    acceso_a(db, usuario, perfil_id, "lector")
    return list(
        db.scalars(
            select(Medicamento).where(Medicamento.perfil_id == perfil_id).order_by(Medicamento.inicio)
        )
    )


def actualizar_medicamento(
    db: Session, usuario: Usuario, medicamento_id: uuid.UUID, cambios: dict
) -> Medicamento:
    """Corrige nombre o dosis (RF-CON-05) o activa/desactiva la pauta. Los campos ausentes no cambian."""
    medicamento = db.get(Medicamento, medicamento_id)
    if medicamento is None:
        raise RecursoNoEncontrado("Medicamento no encontrado")
    acceso_a(db, usuario, medicamento.perfil_id, "editor")
    if cambios.get("nombre") is not None:
        medicamento.nombre = cambios["nombre"]
    if cambios.get("dosis") is not None:
        medicamento.dosis = cambios["dosis"]
    if cambios.get("activo") is not None:
        medicamento.activo = cambios["activo"]
    _auditar(db, "MEDICAMENTO_ACTUALIZADO", usuario.id, medicamento.perfil_id)
    db.commit()
    return medicamento


# ---------- tomas ----------

def _rango_utc(desde: date, hasta: date, zona: ZoneInfo) -> tuple[datetime, datetime]:
    if hasta < desde:
        raise ReglaNegocio("La fecha final no puede ser anterior a la inicial")
    if (hasta - desde).days + 1 > MAX_DIAS_CONSULTA:
        raise ReglaNegocio(f"Consulta hasta {MAX_DIAS_CONSULTA} días")
    inicio = datetime.combine(desde, time(0), tzinfo=zona).astimezone(timezone.utc)
    fin = datetime.combine(hasta + timedelta(days=1), time(0), tzinfo=zona).astimezone(timezone.utc)
    return inicio, fin


def tomas_entre(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, desde: date, hasta: date, zona: ZoneInfo
) -> list[tuple[TomaProgramada, Medicamento, TomaRegistro | None]]:
    acceso_a(db, usuario, perfil_id, "lector")
    inicio, fin = _rango_utc(desde, hasta, zona)
    filas = db.execute(
        select(TomaProgramada, Medicamento)
        .join(Medicamento, Medicamento.id == TomaProgramada.medicamento_id)
        .where(
            Medicamento.perfil_id == perfil_id,
            Medicamento.activo.is_(True),
            TomaProgramada.programada_en >= inicio,
            TomaProgramada.programada_en < fin,
        )
        .order_by(TomaProgramada.programada_en)
    ).all()
    if not filas:
        return []
    ids = [t.id for t, _ in filas]
    registros = db.scalars(
        select(TomaRegistro)
        .where(TomaRegistro.toma_programada_id.in_(ids))
        .order_by(TomaRegistro.registrada_en.desc())
    ).all()
    ultimo: dict[uuid.UUID, TomaRegistro] = {}
    for registro in registros:
        ultimo.setdefault(registro.toma_programada_id, registro)
    return [(toma, med, ultimo.get(toma.id)) for toma, med in filas]


def registrar_toma(
    db: Session,
    usuario: Usuario,
    toma_id: uuid.UUID,
    estado: str,
    registro_id: uuid.UUID | None,
) -> TomaRegistro:
    toma = db.get(TomaProgramada, toma_id)
    if toma is None:
        raise RecursoNoEncontrado("Toma no encontrada")
    medicamento = db.get(Medicamento, toma.medicamento_id)
    acceso_a(db, usuario, medicamento.perfil_id, "editor")
    consentimientos.exigir(db, usuario, "salud")
    if registro_id is not None:
        # Reenvío de la misma toma (p. ej. al reconectar): se devuelve el registro existente.
        existente = db.get(TomaRegistro, registro_id)
        if existente is not None:
            if existente.toma_programada_id != toma_id:
                raise ReglaNegocio("El identificador ya se usó para otra toma")
            return existente
    registro = TomaRegistro(
        id=registro_id or uuid.uuid4(),
        toma_programada_id=toma_id,
        estado=estado,
        registrada_en=ahora_utc(),
        registrada_por=usuario.id,
    )
    db.add(registro)
    _auditar(db, "TOMA_REGISTRADA", usuario.id, medicamento.perfil_id)
    db.commit()
    return registro


# ---------- síntomas ----------

def registrar_sintoma(db: Session, usuario: Usuario, perfil_id: uuid.UUID, datos: dict) -> SintomaRegistro:
    acceso_a(db, usuario, perfil_id, "editor")
    consentimientos.exigir(db, usuario, "salud")
    if datos.get("id") is not None:
        existente = db.get(SintomaRegistro, datos["id"])
        if existente is not None:
            if existente.perfil_id != perfil_id:
                raise ReglaNegocio("El identificador ya se usó en otro perfil")
            return existente
    registro = SintomaRegistro(
        id=datos.get("id") or uuid.uuid4(),
        perfil_id=perfil_id,
        sintoma=datos["sintoma"],
        intensidad=datos["intensidad"],
        nota=datos.get("nota") or None,
        fecha=datos.get("fecha") or ahora_utc(),
        registrado_por=usuario.id,
    )
    db.add(registro)
    _auditar(db, "SINTOMA_REGISTRADO", usuario.id, perfil_id)
    db.commit()
    return registro


def listar_sintomas(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, desde: date, hasta: date, zona: ZoneInfo
) -> list[SintomaRegistro]:
    acceso_a(db, usuario, perfil_id, "lector")
    inicio, fin = _rango_utc(desde, hasta, zona)
    return list(
        db.scalars(
            select(SintomaRegistro)
            .where(
                SintomaRegistro.perfil_id == perfil_id,
                SintomaRegistro.fecha >= inicio,
                SintomaRegistro.fecha < fin,
            )
            .order_by(SintomaRegistro.fecha.desc())
        )
    )


# ---------- diagnósticos ----------

def crear_diagnostico(db: Session, usuario: Usuario, perfil_id: uuid.UUID, datos: dict) -> Diagnostico:
    acceso_a(db, usuario, perfil_id, "editor")
    consentimientos.exigir(db, usuario, "salud")
    zona_id = datos.get("zona_id")
    if zona_id is not None:
        zona = db.get(ZonaConsulta, zona_id)
        if zona is None or zona.perfil_id != perfil_id:
            raise ReglaNegocio("La zona no pertenece a este perfil")
    diagnostico = Diagnostico(
        perfil_id=perfil_id,
        zona_id=zona_id,
        descripcion=datos["descripcion"],
        fecha=datos["fecha"],
        estado=datos.get("estado", "vigente"),
    )
    db.add(diagnostico)
    db.flush()
    _auditar(db, "DIAGNOSTICO_CREADO", usuario.id, perfil_id)
    db.commit()
    return diagnostico


def listar_diagnosticos(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, incluir_resueltos: bool
) -> list[Diagnostico]:
    acceso_a(db, usuario, perfil_id, "lector")
    consulta = select(Diagnostico).where(Diagnostico.perfil_id == perfil_id)
    if not incluir_resueltos:
        consulta = consulta.where(Diagnostico.estado == "vigente")
    return list(db.scalars(consulta.order_by(Diagnostico.fecha.desc())))


def actualizar_diagnostico(
    db: Session, usuario: Usuario, diagnostico_id: uuid.UUID, cambios: dict
) -> Diagnostico:
    diagnostico = db.get(Diagnostico, diagnostico_id)
    if diagnostico is None:
        raise RecursoNoEncontrado("Diagnóstico no encontrado")
    acceso_a(db, usuario, diagnostico.perfil_id, "editor")
    if cambios.get("descripcion") is not None:
        diagnostico.descripcion = cambios["descripcion"]
    if cambios.get("estado") is not None:
        diagnostico.estado = cambios["estado"]
    _auditar(db, "DIAGNOSTICO_ACTUALIZADO", usuario.id, diagnostico.perfil_id)
    db.commit()
    return diagnostico
