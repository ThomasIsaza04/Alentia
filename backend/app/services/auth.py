"""Reglas de autenticación: registro, verificación, sesiones, bloqueo y recuperación.

Los endpoints solo llaman a estas funciones. Ninguna respuesta revela si un correo existe (RF-AUT-01 y RF-AUT-04).
"""
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import passwords
from app.core.config import settings
from app.core.errores import (
    AccionInvalida,
    CredencialesInvalidas,
    CuentaNoVerificada,
    SesionInvalida,
)
from app.core.tokens import crear_access_token, hash_token, token_aleatorio
from app.db.base import ahora_utc
from app.models import Auditoria, SesionRefresh, TokenAccion, Usuario
from app.services.correo import MensajeCorreo, remitente

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15
HORAS_VERIFICACION = 24
MINUTOS_RECUPERACION = 30
# Una sola respuesta para credencial incorrecta, cuenta inexistente y cuenta bloqueada:
# así nadie puede saber qué correos están registrados ni cuáles están bloqueados (RF-AUT-03).
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"


def _normalizar(correo: str) -> str:
    return correo.strip().lower()


def _auditar(db: Session, accion: str, actor: uuid.UUID | None = None) -> None:
    db.add(Auditoria(accion=accion, actor_usuario_id=actor, fecha=ahora_utc()))


def _usuario_por_correo(db: Session, correo: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.correo == _normalizar(correo)))


def _emitir_accion(db: Session, usuario: Usuario, tipo: str, vigencia: timedelta) -> str:
    token = token_aleatorio()
    ahora = ahora_utc()
    db.add(
        TokenAccion(
            usuario_id=usuario.id,
            tipo=tipo,
            hash_token=hash_token(token),
            creado_en=ahora,
            expira_en=ahora + vigencia,
        )
    )
    return token


def _buscar_accion(db: Session, token: str, tipo: str) -> TokenAccion | None:
    return db.scalar(
        select(TokenAccion).where(
            TokenAccion.hash_token == hash_token(token),
            TokenAccion.tipo == tipo,
            TokenAccion.usado_en.is_(None),
            TokenAccion.expira_en > ahora_utc(),
        )
    )


def _enlace(ruta: str, token: str) -> str:
    return f"{settings.frontend_url}/{ruta}?token={token}"


def _emitir_sesion(db: Session, usuario_id: uuid.UUID, familia_id: uuid.UUID) -> str:
    token = token_aleatorio()
    ahora = ahora_utc()
    db.add(
        SesionRefresh(
            usuario_id=usuario_id,
            familia_id=familia_id,
            hash_token=hash_token(token),
            creada_en=ahora,
            expira_en=ahora + timedelta(days=settings.refresh_dias),
        )
    )
    return token


def registrar(db: Session, correo: str, clave: str) -> None:
    passwords.validar_politica(clave)
    correo_normalizado = _normalizar(correo)
    # El hash se calcula siempre, exista o no el correo, para igualar el tiempo de respuesta.
    hash_nuevo = passwords.hashear(clave)
    if _usuario_por_correo(db, correo_normalizado) is None:
        usuario = Usuario(correo=correo_normalizado, hash_contrasena=hash_nuevo)
        db.add(usuario)
        db.flush()
        token = _emitir_accion(db, usuario, "verificacion", timedelta(hours=HORAS_VERIFICACION))
        _auditar(db, "REGISTRO", usuario.id)
        db.commit()
        remitente.enviar(
            MensajeCorreo(
                correo_normalizado,
                "Verifica tu correo en Alentia",
                f"Enlace de verificación (válido 24 horas): {_enlace('verificar', token)}",
            )
        )


def reenviar_verificacion(db: Session, correo: str) -> None:
    usuario = _usuario_por_correo(db, correo)
    if usuario is not None and not usuario.verificado:
        token = _emitir_accion(db, usuario, "verificacion", timedelta(hours=HORAS_VERIFICACION))
        db.commit()
        remitente.enviar(
            MensajeCorreo(
                usuario.correo,
                "Verifica tu correo en Alentia",
                f"Enlace de verificación (válido 24 horas): {_enlace('verificar', token)}",
            )
        )


def verificar_correo(db: Session, token: str) -> None:
    accion = _buscar_accion(db, token, "verificacion")
    if accion is None:
        raise AccionInvalida("El enlace no es válido, venció o ya fue usado")
    usuario = db.get(Usuario, accion.usuario_id)
    usuario.verificado = True
    accion.usado_en = ahora_utc()
    db.commit()


def iniciar_sesion(db: Session, correo: str, clave: str) -> tuple[str, str]:
    usuario = _usuario_por_correo(db, correo)
    if usuario is None:
        passwords.verificar(clave, passwords.HASH_FICTICIO)
        raise CredencialesInvalidas(MENSAJE_CREDENCIALES)

    ahora = ahora_utc()
    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora:
        # Se verifica igualmente la clave para que el tiempo de respuesta no delate el bloqueo.
        passwords.verificar(clave, usuario.hash_contrasena)
        _auditar(db, "LOGIN_BLOQUEADO", usuario.id)
        db.commit()
        raise CredencialesInvalidas(MENSAJE_CREDENCIALES)

    if not passwords.verificar(clave, usuario.hash_contrasena):
        usuario.intentos_fallidos += 1
        _auditar(db, "LOGIN_FALLIDO", usuario.id)
        if usuario.intentos_fallidos >= MAX_INTENTOS:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
            usuario.intentos_fallidos = 0
            _auditar(db, "CUENTA_BLOQUEADA", usuario.id)
        db.commit()
        raise CredencialesInvalidas(MENSAJE_CREDENCIALES)

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    if not usuario.verificado:
        db.commit()
        raise CuentaNoVerificada("Verifica tu correo antes de iniciar sesión")

    if passwords.necesita_rehash(usuario.hash_contrasena):
        usuario.hash_contrasena = passwords.hashear(clave)

    acceso = crear_access_token(usuario.id)
    refresco = _emitir_sesion(db, usuario.id, uuid.uuid4())
    _auditar(db, "LOGIN", usuario.id)
    db.commit()
    return acceso, refresco


def rotar_sesion(db: Session, refresco: str) -> tuple[str, str]:
    sesion = db.scalar(select(SesionRefresh).where(SesionRefresh.hash_token == hash_token(refresco)))
    if sesion is None:
        raise SesionInvalida("La sesión no es válida. Inicia sesión de nuevo")

    if sesion.usada_en is not None:
        # Un token ya rotado volvió a usarse: se asume robo y se cierran todas las sesiones del usuario.
        db.execute(
            update(SesionRefresh)
            .where(SesionRefresh.usuario_id == sesion.usuario_id)
            .values(revocada=True)
        )
        _auditar(db, "REUTILIZACION_REFRESH", sesion.usuario_id)
        db.commit()
        raise SesionInvalida("La sesión no es válida. Inicia sesión de nuevo")

    if sesion.revocada or sesion.expira_en <= ahora_utc():
        raise SesionInvalida("La sesión no es válida. Inicia sesión de nuevo")

    sesion.usada_en = ahora_utc()
    nuevo_refresco = _emitir_sesion(db, sesion.usuario_id, sesion.familia_id)
    acceso = crear_access_token(sesion.usuario_id)
    db.commit()
    return acceso, nuevo_refresco


def cerrar_sesion(db: Session, refresco: str | None) -> None:
    if not refresco:
        return
    sesion = db.scalar(select(SesionRefresh).where(SesionRefresh.hash_token == hash_token(refresco)))
    if sesion is not None:
        sesion.revocada = True
        _auditar(db, "LOGOUT", sesion.usuario_id)
        db.commit()


def solicitar_recuperacion(db: Session, correo: str) -> None:
    usuario = _usuario_por_correo(db, correo)
    if usuario is not None:
        token = _emitir_accion(db, usuario, "recuperacion", timedelta(minutes=MINUTOS_RECUPERACION))
        db.commit()
        remitente.enviar(
            MensajeCorreo(
                usuario.correo,
                "Recupera tu contraseña de Alentia",
                f"Enlace para restablecer la contraseña (válido 30 minutos): {_enlace('restablecer', token)}",
            )
        )


def restablecer_clave(db: Session, token: str, nueva_clave: str) -> None:
    passwords.validar_politica(nueva_clave)
    accion = _buscar_accion(db, token, "recuperacion")
    if accion is None:
        raise AccionInvalida("El enlace no es válido, venció o ya fue usado")

    usuario = db.get(Usuario, accion.usuario_id)
    usuario.hash_contrasena = passwords.hashear(nueva_clave)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    accion.usado_en = ahora_utc()
    # Al cambiar la contraseña se cierran todas las sesiones anteriores. Los datos de salud no se pierden (§7.3).
    db.execute(
        update(SesionRefresh).where(SesionRefresh.usuario_id == usuario.id).values(revocada=True)
    )
    _auditar(db, "RECUPERACION_CLAVE", usuario.id)
    db.commit()
