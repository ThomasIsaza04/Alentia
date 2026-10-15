"""Registros de salud: medicación, tomas, síntomas y diagnósticos (pasos 5 y 6)."""
import json
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import usuario_verificado
from app.core.config import settings
from app.db.base import ahora_utc
from app.db.session import get_db
from app.models import Usuario
from app.schemas.salud import (
    DiagnosticoEstadoIn,
    DiagnosticoIn,
    DiagnosticoOut,
    MedicamentoActualizarIn,
    MedicamentoIn,
    MedicamentoOut,
    RegistroTomaIn,
    RegistroTomaOut,
    SintomaIn,
    SintomaOut,
    TomaOut,
)
from app.services import salud as servicio
from app.services import tareas as servicio_tareas

router = APIRouter(tags=["salud"], prefix="/api/v1")


def _medicamento_out(m) -> MedicamentoOut:
    return MedicamentoOut(
        id=m.id,
        perfil_id=m.perfil_id,
        nombre=m.nombre,
        dosis=m.dosis,
        frecuencia=json.loads(m.frecuencia),
        inicio=m.inicio,
        fin=m.fin,
        activo=m.activo,
    )


def _zona_de(consulta: str | None):
    return servicio.zona_valida(consulta or settings.zona_horaria_por_defecto)


@router.post("/perfiles/{perfil_id}/medicamentos", status_code=201, response_model=MedicamentoOut)
def crear_medicamento(
    perfil_id: uuid.UUID,
    datos: MedicamentoIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> MedicamentoOut:
    medicamento = servicio.crear_medicamento(
        db,
        usuario,
        perfil_id,
        {
            "nombre": datos.nombre.strip(),
            "dosis": datos.dosis.strip(),
            "frecuencia": datos.frecuencia.model_dump(),
            "inicio": datos.inicio,
            "fin": datos.fin,
            "zona_horaria": datos.zona_horaria,
        },
    )
    return _medicamento_out(medicamento)


@router.get("/perfiles/{perfil_id}/medicamentos", response_model=list[MedicamentoOut])
def listar_medicamentos(
    perfil_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[MedicamentoOut]:
    return [_medicamento_out(m) for m in servicio.listar_medicamentos(db, usuario, perfil_id)]


@router.patch("/medicamentos/{medicamento_id}", response_model=MedicamentoOut)
def actualizar_medicamento(
    medicamento_id: uuid.UUID,
    datos: MedicamentoActualizarIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> MedicamentoOut:
    cambios = datos.model_dump(exclude_unset=True)
    return _medicamento_out(servicio.actualizar_medicamento(db, usuario, medicamento_id, cambios))


@router.get("/perfiles/{perfil_id}/tomas", response_model=list[TomaOut])
def listar_tomas(
    perfil_id: uuid.UUID,
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    zona_horaria: str | None = Query(default=None, max_length=60),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[TomaOut]:
    zona = _zona_de(zona_horaria)
    ahora = ahora_utc()
    hoy = ahora.astimezone(zona).date()
    filas = servicio.tomas_entre(db, usuario, perfil_id, desde or hoy, hasta or desde or hoy, zona)
    salida = []
    for toma, medicamento, registro in filas:
        local = toma.programada_en.astimezone(zona)
        salida.append(
            TomaOut(
                id=toma.id,
                medicamento_id=medicamento.id,
                nombre=medicamento.nombre,
                dosis=medicamento.dosis,
                programada_en=toma.programada_en,
                fecha_local=local.date().isoformat(),
                hora_local=local.strftime("%H:%M"),
                estado=servicio_tareas.estado_atraso(toma.programada_en, registro.estado if registro else None, ahora),
                registro_id=registro.id if registro else None,
            )
        )
    return salida


@router.post("/tomas/{toma_id}/registros", status_code=201, response_model=RegistroTomaOut)
def registrar_toma(
    toma_id: uuid.UUID,
    datos: RegistroTomaIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> RegistroTomaOut:
    registro = servicio.registrar_toma(db, usuario, toma_id, datos.estado, datos.id)
    return RegistroTomaOut(
        id=registro.id,
        toma_id=registro.toma_programada_id,
        estado=registro.estado,
        registrada_en=registro.registrada_en,
    )


@router.post("/perfiles/{perfil_id}/sintomas", status_code=201, response_model=SintomaOut)
def registrar_sintoma(
    perfil_id: uuid.UUID,
    datos: SintomaIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> SintomaOut:
    registro = servicio.registrar_sintoma(
        db,
        usuario,
        perfil_id,
        {
            "sintoma": datos.sintoma.strip(),
            "intensidad": datos.intensidad,
            "nota": datos.nota.strip() if datos.nota else None,
            "fecha": datos.fecha,
            "id": datos.id,
        },
    )
    return SintomaOut(
        id=registro.id,
        sintoma=registro.sintoma,
        intensidad=registro.intensidad,
        nota=registro.nota,
        fecha=registro.fecha,
    )


@router.get("/perfiles/{perfil_id}/sintomas", response_model=list[SintomaOut])
def listar_sintomas(
    perfil_id: uuid.UUID,
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    zona_horaria: str | None = Query(default=None, max_length=60),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[SintomaOut]:
    zona = _zona_de(zona_horaria)
    hoy = ahora_utc().astimezone(zona).date()
    filas = servicio.listar_sintomas(db, usuario, perfil_id, desde or hoy, hasta or hoy, zona)
    return [
        SintomaOut(id=r.id, sintoma=r.sintoma, intensidad=r.intensidad, nota=r.nota, fecha=r.fecha)
        for r in filas
    ]


@router.post("/perfiles/{perfil_id}/diagnosticos", status_code=201, response_model=DiagnosticoOut)
def crear_diagnostico(
    perfil_id: uuid.UUID,
    datos: DiagnosticoIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> DiagnosticoOut:
    d = servicio.crear_diagnostico(
        db,
        usuario,
        perfil_id,
        {
            "descripcion": datos.descripcion.strip(),
            "fecha": datos.fecha,
            "zona_id": datos.zona_id,
            "estado": datos.estado,
        },
    )
    return DiagnosticoOut(id=d.id, descripcion=d.descripcion, fecha=d.fecha, estado=d.estado, zona_id=d.zona_id)


@router.get("/perfiles/{perfil_id}/diagnosticos", response_model=list[DiagnosticoOut])
def listar_diagnosticos(
    perfil_id: uuid.UUID,
    incluir_resueltos: bool = Query(default=True),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[DiagnosticoOut]:
    filas = servicio.listar_diagnosticos(db, usuario, perfil_id, incluir_resueltos)
    return [
        DiagnosticoOut(id=d.id, descripcion=d.descripcion, fecha=d.fecha, estado=d.estado, zona_id=d.zona_id)
        for d in filas
    ]


@router.patch("/diagnosticos/{diagnostico_id}", response_model=DiagnosticoOut)
def cambiar_estado_diagnostico(
    diagnostico_id: uuid.UUID,
    datos: DiagnosticoEstadoIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> DiagnosticoOut:
    d = servicio.actualizar_diagnostico(db, usuario, diagnostico_id, datos.model_dump(exclude_unset=True))
    return DiagnosticoOut(id=d.id, descripcion=d.descripcion, fecha=d.fecha, estado=d.estado, zona_id=d.zona_id)
