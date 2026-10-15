"""Perfiles, zonas de consulta y vínculos entre cuentas (paso 4, §9.6).

Rutas: /api/v1/perfiles, /api/v1/zonas, /api/v1/invitaciones.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import usuario_verificado
from app.db.session import get_db
from app.models import Perfil, Usuario, ZonaConsulta
from app.schemas.auth import MensajeOut
from app.schemas.perfiles import (
    AccesoOut,
    InvitacionAceptarIn,
    InvitacionIn,
    PerfilActualizarIn,
    PerfilIn,
    PerfilOut,
    ZonaActualizarIn,
    ZonaIn,
    ZonaOut,
)
from app.services import perfiles as servicio

router = APIRouter(prefix="/perfiles", tags=["perfiles"])
router_zonas = APIRouter(prefix="/zonas", tags=["zonas de consulta"])
router_invitaciones = APIRouter(prefix="/invitaciones", tags=["vínculos"])


def _perfil_out(perfil, acceso) -> PerfilOut:
    return PerfilOut(
        id=perfil.id,
        nombre=perfil.nombre,
        fecha_nacimiento=perfil.fecha_nacimiento,
        dependiente=perfil.titular_usuario_id is None,
        rol=acceso.rol,
        alcance=acceso.alcance,
    )


def _zona_out(zona: ZonaConsulta) -> ZonaOut:
    return ZonaOut(id=zona.id, perfil_id=zona.perfil_id, nombre=zona.nombre, archivada=zona.archivada)


@router.post("", status_code=201, response_model=PerfilOut)
def crear_perfil(
    datos: PerfilIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> PerfilOut:
    perfil, acceso = servicio.crear_perfil(
        db, usuario, datos.nombre.strip(), datos.fecha_nacimiento, datos.dependiente
    )
    return _perfil_out(perfil, acceso)


@router.get("", response_model=list[PerfilOut])
def listar_perfiles(
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[PerfilOut]:
    return [_perfil_out(p, a) for p, a in servicio.perfiles_de(db, usuario)]


@router.get("/{perfil_id}", response_model=PerfilOut)
def consultar_perfil(
    perfil_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> PerfilOut:
    acceso = servicio.acceso_a(db, usuario, perfil_id, "lector")
    perfil = db.get(Perfil, perfil_id)
    return _perfil_out(perfil, acceso)


@router.patch("/{perfil_id}", response_model=PerfilOut)
def actualizar_perfil(
    perfil_id: uuid.UUID,
    datos: PerfilActualizarIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> PerfilOut:
    nombre = datos.nombre.strip() if datos.nombre is not None else None
    perfil, acceso = servicio.actualizar_perfil(db, usuario, perfil_id, nombre, datos.fecha_nacimiento)
    return _perfil_out(perfil, acceso)


@router.get("/{perfil_id}/zonas", response_model=list[ZonaOut])
def listar_zonas(
    perfil_id: uuid.UUID,
    incluir_archivadas: bool = Query(default=False),
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[ZonaOut]:
    return [_zona_out(z) for z in servicio.listar_zonas(db, usuario, perfil_id, incluir_archivadas)]


@router.post("/{perfil_id}/zonas", status_code=201, response_model=ZonaOut)
def crear_zona(
    perfil_id: uuid.UUID,
    datos: ZonaIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> ZonaOut:
    return _zona_out(servicio.crear_zona(db, usuario, perfil_id, datos.nombre.strip()))


@router.get("/{perfil_id}/accesos", response_model=list[AccesoOut])
def listar_accesos(
    perfil_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> list[AccesoOut]:
    return [
        AccesoOut(
            id=a.id,
            usuario_id=a.usuario_id,
            correo=correo,
            rol=a.rol,
            alcance=a.alcance,
            estado=a.estado,
            inicio=a.inicio,
        )
        for a, correo in servicio.listar_accesos(db, usuario, perfil_id)
    ]


@router.post("/{perfil_id}/invitaciones", status_code=202, response_model=MensajeOut)
def invitar(
    perfil_id: uuid.UUID,
    datos: InvitacionIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> MensajeOut:
    servicio.invitar(db, usuario, perfil_id, datos.correo, datos.alcance)
    return MensajeOut(mensaje="Si el correo es válido, se envió la invitación")


@router.delete("/{perfil_id}/accesos/{acceso_id}", response_model=MensajeOut)
def revocar_acceso(
    perfil_id: uuid.UUID,
    acceso_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> MensajeOut:
    servicio.revocar_acceso(db, usuario, perfil_id, acceso_id)
    return MensajeOut(mensaje="Acceso revocado")


@router_zonas.patch("/{zona_id}", response_model=ZonaOut)
def actualizar_zona(
    zona_id: uuid.UUID,
    datos: ZonaActualizarIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> ZonaOut:
    nombre = datos.nombre.strip() if datos.nombre is not None else None
    return _zona_out(servicio.actualizar_zona(db, usuario, zona_id, nombre, datos.archivada))


@router_invitaciones.post("/aceptar", response_model=MensajeOut)
def aceptar_invitacion(
    datos: InvitacionAceptarIn,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(get_db),
) -> MensajeOut:
    servicio.aceptar_invitacion(db, usuario, datos.token)
    return MensajeOut(mensaje="Invitación aceptada")
