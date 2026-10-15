"""Acceso temporal del profesional por QR y PIN (paso 7).

Las rutas de /acceso-profesional no requieren cuenta. Sus respuestas llevan
Cache-Control: no-store y Referrer-Policy: no-referrer (RF-QRM-03).
"""
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import usuario_verificado
from app.db.base import ahora_utc
from app.db.session import get_db
from app.models import AccesoTemporal, Perfil, Usuario
from app.schemas.acceso_temporal import (
    AbrirIn,
    AbrirOut,
    AccesoOut,
    CrearAccesoIn,
    CrearAccesoOut,
    EventoOut,
    VerificarIn,
    VerificarOut,
)
from app.core.errores import SesionInvalida
from app.services import acceso_temporal as servicio
from app.services.resumen import construir_resumen, reunir_datos

router = APIRouter(tags=["acceso temporal"], prefix="/api/v1")


def _dispositivo(request: Request) -> str:
    ua = request.headers.get("user-agent", "").lower()
    if not ua:
        return "desconocido"
    if any(marca in ua for marca in ("mobi", "android", "iphone")):
        return "movil"
    return "escritorio"


def _no_guardar(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


def _acceso_out(a: AccesoTemporal, ahora) -> AccesoOut:
    return AccesoOut(
        id=a.id,
        categorias=a.categorias.split(","),
        duracion_minutos=a.duracion_minutos,
        creado_en=a.creado_en,
        vence_en=a.vence_en,
        estado=servicio.estado_de(a, ahora),
        consumido_en=a.consumido_en,
        bloqueado_en=a.bloqueado_en,
        revocado_en=a.revocado_en,
    )


# ---------- titular ----------

@router.post("/perfiles/{perfil_id}/accesos-temporales", status_code=201, response_model=CrearAccesoOut)
def crear_acceso(
    perfil_id: uuid.UUID,
    datos: CrearAccesoIn,
    request: Request,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> CrearAccesoOut:
    acceso, token, pin = servicio.crear(
        db, usuario, perfil_id, datos.categorias, datos.duracion_minutos, _dispositivo(request)
    )
    return CrearAccesoOut(
        id=acceso.id,
        categorias=acceso.categorias.split(","),
        duracion_minutos=acceso.duracion_minutos,
        vence_en=acceso.vence_en,
        token=token,
        pin=pin,
        enlace_path=f"/acceso/{token}",
    )


@router.get("/perfiles/{perfil_id}/accesos-temporales", response_model=list[AccesoOut])
def listar_accesos(
    perfil_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[AccesoOut]:
    ahora = ahora_utc()
    return [_acceso_out(a, ahora) for a in servicio.listar(db, usuario, perfil_id)]


@router.get("/accesos-temporales/{acceso_id}/bitacora", response_model=list[EventoOut])
def ver_bitacora(
    acceso_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[EventoOut]:
    return [
        EventoOut(tipo=e.tipo, ocurrido_en=e.ocurrido_en, tipo_dispositivo=e.tipo_dispositivo)
        for e in servicio.bitacora(db, usuario, acceso_id)
    ]


@router.post("/accesos-temporales/{acceso_id}/revocar", response_model=AccesoOut)
def revocar_acceso(
    acceso_id: uuid.UUID,
    request: Request,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> AccesoOut:
    acceso = servicio.revocar(db, usuario, acceso_id, _dispositivo(request))
    return _acceso_out(acceso, ahora_utc())


# ---------- profesional ----------

@router.post("/acceso-profesional/abrir", response_model=AbrirOut)
def abrir_acceso(
    datos: AbrirIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AbrirOut:
    _no_guardar(response)
    acceso = servicio.abrir(db, datos.token, _dispositivo(request))
    return AbrirOut(requiere_pin=True, vence_en=acceso.vence_en)


@router.post("/acceso-profesional/verificar", response_model=VerificarOut)
def verificar_acceso(
    datos: VerificarIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> VerificarOut:
    _no_guardar(response)
    sesion, vence = servicio.verificar_pin(db, datos.token, datos.pin, _dispositivo(request))
    return VerificarOut(sesion_token=sesion, vence_en=vence)


def sesion_profesional(
    response: Response,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccesoTemporal:
    _no_guardar(response)
    if not authorization or not authorization.startswith("Bearer "):
        raise SesionInvalida("Abre el enlace y verifica el PIN para continuar")
    return servicio.acceso_de_sesion(db, authorization.removeprefix("Bearer ").strip())


@router.get("/acceso-profesional/resumen")
def resumen_profesional(
    acceso: AccesoTemporal = Depends(sesion_profesional),
    db: Session = Depends(get_db),
) -> dict:
    ahora = ahora_utc()
    perfil = db.get(Perfil, acceso.perfil_id)
    datos = reunir_datos(db, acceso.perfil_id, ahora)
    salida = construir_resumen(acceso.categorias.split(","), datos)
    salida["perfil_nombre"] = perfil.nombre if perfil else ""
    salida["generado_en"] = ahora.isoformat()
    salida["aviso"] = "Datos aportados por el paciente. No constituyen un diagnóstico médico."
    return salida
