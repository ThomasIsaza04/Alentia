from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errores import CuentaNoVerificada, SesionInvalida
from app.core.tokens import leer_access_token
from app.db.session import get_db
from app.models import Usuario


def usuario_actual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    if not authorization or not authorization.startswith("Bearer "):
        raise SesionInvalida("Inicia sesión para continuar")
    usuario_id = leer_access_token(authorization.removeprefix("Bearer ").strip())
    if usuario_id is None:
        raise SesionInvalida("La sesión expiró. Vuelve a iniciar sesión")
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise SesionInvalida("La sesión no es válida. Inicia sesión de nuevo")
    return usuario


def usuario_verificado(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Para operaciones sobre datos de salud: la cuenta debe tener el correo verificado."""
    if not usuario.verificado:
        raise CuentaNoVerificada("Debes verificar tu correo antes de continuar")
    return usuario
