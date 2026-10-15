"""Hash de contraseñas con Argon2id y política mínima (RF-AUT-01, RNF01)."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.errores import ContrasenaDebil

LONGITUD_MINIMA = 10
LONGITUD_MAXIMA = 128

# Lista mínima de contraseñas comunes. Antes de la sustentación se reemplaza por una lista completa.
CLAVES_COMUNES = frozenset(
    {
        "1234567890",
        "12345678910",
        "password123",
        "contraseña123",
        "contrasena123",
        "qwertyuiop",
        "abcdefghij",
        "alentia1234",
    }
)

_hasher = PasswordHasher()  # argon2-cffi usa Argon2id por defecto


def validar_politica(clave: str) -> None:
    if len(clave) < LONGITUD_MINIMA:
        raise ContrasenaDebil(f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres")
    if len(clave) > LONGITUD_MAXIMA:
        raise ContrasenaDebil(f"La contraseña no puede tener más de {LONGITUD_MAXIMA} caracteres")
    if clave.lower() in CLAVES_COMUNES:
        raise ContrasenaDebil("Esa contraseña es demasiado común. Elige otra")


def hashear(clave: str) -> str:
    return _hasher.hash(clave)


def verificar(clave: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, clave)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def necesita_rehash(hash_guardado: str) -> bool:
    return _hasher.check_needs_rehash(hash_guardado)


# Se usa cuando el correo no existe, para que el tiempo de respuesta no revele si la cuenta existe.
HASH_FICTICIO = _hasher.hash("contrasena-ficticia-para-igualar-tiempos")
