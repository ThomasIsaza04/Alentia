"""Cuenta del titular: consentimiento, exportación y eliminación (paso 8)."""
import json

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual, usuario_verificado
from app.db.session import get_db
from app.models import Usuario
from app.schemas.cuenta import ConsentimientoIn, EliminacionIn, EliminacionOut
from app.services import consentimiento as consentimientos
from app.services import cuenta as servicio

router = APIRouter(prefix="/api/v1/cuenta", tags=["cuenta"])


@router.get("/consentimientos")
def ver_consentimientos(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)) -> dict:
    return {"politica": consentimientos.politica(), "estado": consentimientos.estado(db, usuario)}


@router.post("/consentimientos")
def registrar_consentimiento(
    datos: ConsentimientoIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> dict:
    estado = consentimientos.registrar(db, usuario, datos.finalidad, datos.version, datos.aceptado)
    return {"politica": consentimientos.politica(), "estado": estado}


@router.get("/exportacion")
def exportar(
    formato: str = Query(default="json", pattern="^(json|csv)$"),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> Response:
    datos = servicio.datos_exportacion(db, usuario)
    cabeceras = {"Cache-Control": "no-store"}
    if formato == "csv":
        cabeceras["Content-Disposition"] = 'attachment; filename="alentia-datos.csv"'
        return Response(servicio.exportacion_csv(datos), media_type="text/csv; charset=utf-8", headers=cabeceras)
    cabeceras["Content-Disposition"] = 'attachment; filename="alentia-datos.json"'
    return JSONResponse(content=json.loads(json.dumps(datos, ensure_ascii=False)), headers=cabeceras)


@router.get("/eliminacion", response_model=EliminacionOut)
def ver_eliminacion(usuario: Usuario = Depends(usuario_actual)) -> EliminacionOut:
    return EliminacionOut(eliminar_en=usuario.eliminar_en)


@router.post("/eliminacion", response_model=EliminacionOut)
def solicitar_eliminacion(
    datos: EliminacionIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> EliminacionOut:
    return EliminacionOut(eliminar_en=servicio.solicitar_eliminacion(db, usuario, datos.clave))


@router.post("/eliminacion/cancelar", response_model=EliminacionOut)
def cancelar_eliminacion(
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> EliminacionOut:
    servicio.cancelar_eliminacion(db, usuario)
    return EliminacionOut(eliminar_en=None)
