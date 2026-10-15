"""Endpoints de autenticación (RF-AUT-01 a RF-AUT-04). Prefijo: /api/v1/auth."""
from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.core.config import settings
from app.core.errores import SesionInvalida
from app.db.session import get_db
from app.models import Usuario
from app.schemas.auth import (
    AccesoOut,
    CorreoIn,
    LoginIn,
    MensajeOut,
    RegistroIn,
    RestablecerIn,
    TokenIn,
    UsuarioOut,
)
from app.services import auth as servicio

router = APIRouter(prefix="/auth", tags=["autenticación"])

NOMBRE_COOKIE = "refresh_token"
RUTA_COOKIE = "/api/v1/auth"
MENSAJE_GENERICO = "Si los datos son válidos, recibirás un correo con las instrucciones."


def _poner_cookie_refresco(response: Response, token: str) -> None:
    response.set_cookie(
        key=NOMBRE_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=RUTA_COOKIE,
        max_age=settings.refresh_dias * 86400,
    )


@router.post("/register", status_code=202, response_model=MensajeOut)
def registrar(datos: RegistroIn, db: Session = Depends(get_db)) -> MensajeOut:
    servicio.registrar(db, datos.correo, datos.clave)
    return MensajeOut(mensaje=MENSAJE_GENERICO)


@router.post("/reenviar-verificacion", status_code=202, response_model=MensajeOut)
def reenviar_verificacion(datos: CorreoIn, db: Session = Depends(get_db)) -> MensajeOut:
    servicio.reenviar_verificacion(db, datos.correo)
    return MensajeOut(mensaje=MENSAJE_GENERICO)


@router.post("/verify-email", response_model=MensajeOut)
def verificar_correo(datos: TokenIn, db: Session = Depends(get_db)) -> MensajeOut:
    servicio.verificar_correo(db, datos.token)
    return MensajeOut(mensaje="Correo verificado. Ya puedes iniciar sesión")


@router.post("/login", response_model=AccesoOut)
def iniciar_sesion(datos: LoginIn, response: Response, db: Session = Depends(get_db)) -> AccesoOut:
    acceso, refresco = servicio.iniciar_sesion(db, datos.correo, datos.clave)
    _poner_cookie_refresco(response, refresco)
    return AccesoOut(access_token=acceso)


@router.post("/refresh", response_model=AccesoOut)
def refrescar(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> AccesoOut:
    if not refresh_token:
        raise SesionInvalida("Inicia sesión de nuevo")
    acceso, nuevo = servicio.rotar_sesion(db, refresh_token)
    _poner_cookie_refresco(response, nuevo)
    return AccesoOut(access_token=acceso)


@router.post("/logout", response_model=MensajeOut)
def cerrar_sesion(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> MensajeOut:
    servicio.cerrar_sesion(db, refresh_token)
    response.delete_cookie(NOMBRE_COOKIE, path=RUTA_COOKIE)
    return MensajeOut(mensaje="Sesión cerrada")


@router.post("/forgot-password", status_code=202, response_model=MensajeOut)
def olvide_mi_clave(datos: CorreoIn, db: Session = Depends(get_db)) -> MensajeOut:
    servicio.solicitar_recuperacion(db, datos.correo)
    return MensajeOut(mensaje=MENSAJE_GENERICO)


@router.post("/reset-password", response_model=MensajeOut)
def restablecer_clave(datos: RestablecerIn, db: Session = Depends(get_db)) -> MensajeOut:
    servicio.restablecer_clave(db, datos.token, datos.clave)
    return MensajeOut(mensaje="Contraseña actualizada. Inicia sesión con la nueva")


@router.get("/me", response_model=UsuarioOut)
def mi_cuenta(usuario: Usuario = Depends(usuario_actual)) -> UsuarioOut:
    return UsuarioOut(id=usuario.id, correo=usuario.correo, verificado=usuario.verificado)
