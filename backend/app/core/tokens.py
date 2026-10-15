"""Tokens de acceso (JWT HS256, 15 minutos) y tokens opacos de un solo uso (§7.5, §7.4)."""
import hashlib
import secrets
import uuid
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.errores import ErrorConfiguracion
from app.db.base import ahora_utc

ALGORITMO = "HS256"


def _secreto() -> str:
    if len(settings.jwt_secret) < 32:
        raise ErrorConfiguracion("JWT_SECRET debe tener al menos 32 caracteres")
    return settings.jwt_secret


def crear_access_token(usuario_id: uuid.UUID) -> str:
    ahora = ahora_utc()
    payload = {
        "sub": str(usuario_id),
        "typ": "access",
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.access_token_minutos),
    }
    return jwt.encode(payload, _secreto(), algorithm=ALGORITMO)


def leer_access_token(token: str) -> uuid.UUID | None:
    try:
        datos = jwt.decode(
            token, _secreto(), algorithms=[ALGORITMO], options={"require": ["exp", "iat", "sub"]}
        )
    except jwt.PyJWTError:
        return None
    if datos.get("typ") != "access":
        return None
    try:
        return uuid.UUID(datos["sub"])
    except (ValueError, TypeError):
        return None


def token_aleatorio() -> str:
    """256 bits de entropía (RF-QRM-01 usa la misma longitud)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Solo el hash se guarda en la base de datos; el token en claro nunca se persiste."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
