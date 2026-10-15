"""Cifrado AES-256-GCM con identificador de llave (§7.3 y ADR-05).

Formato del valor almacenado:  v1:<id_llave>:<base64(nonce + texto_cifrado)>
Las llaves viven en variables de entorno del servidor, nunca en el repositorio, y
no se derivan de la contraseña del usuario.
"""
import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

VERSION = "v1"
LONGITUD_NONCE = 12
LONGITUD_LLAVE = 32


class ErrorCifrado(Exception):
    """Error de cifrado o descifrado. Nunca incluye el texto en claro."""


def _llave(kid: str) -> bytes:
    if kid not in settings.encryption_keys:
        raise ErrorCifrado(f"La llave '{kid}' no está configurada")
    llave = base64.b64decode(settings.encryption_keys[kid])
    if len(llave) != LONGITUD_LLAVE:
        raise ErrorCifrado(f"La llave '{kid}' debe tener 32 bytes")
    return llave


def cifrar(texto: str, contexto: str) -> str:
    kid = settings.encryption_active_key_id
    nonce = os.urandom(LONGITUD_NONCE)
    texto_cifrado = AESGCM(_llave(kid)).encrypt(
        nonce, texto.encode("utf-8"), contexto.encode("utf-8")
    )
    cuerpo = base64.b64encode(nonce + texto_cifrado).decode("ascii")
    return f"{VERSION}:{kid}:{cuerpo}"


def descifrar(valor: str, contexto: str) -> str:
    partes = valor.split(":", 2)
    if len(partes) != 3 or partes[0] != VERSION:
        raise ErrorCifrado("Formato de dato cifrado no reconocido")
    _, kid, cuerpo = partes
    datos = base64.b64decode(cuerpo)
    nonce, texto_cifrado = datos[:LONGITUD_NONCE], datos[LONGITUD_NONCE:]
    try:
        claro = AESGCM(_llave(kid)).decrypt(nonce, texto_cifrado, contexto.encode("utf-8"))
    except InvalidTag:
        raise ErrorCifrado("No se pudo descifrar: datos alterados o contexto incorrecto") from None
    return claro.decode("utf-8")
