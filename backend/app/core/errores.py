"""Errores de dominio. La API los convierte en respuestas tipo RFC 7807 (application/problem+json)."""


class ErrorAuth(Exception):
    status_code = 400
    titulo = "Solicitud no válida"

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle)
        self.detalle = detalle


class ContrasenaDebil(ErrorAuth):
    status_code = 422
    titulo = "Contraseña no válida"


class CredencialesInvalidas(ErrorAuth):
    status_code = 401
    titulo = "Credenciales inválidas"


class CuentaNoVerificada(ErrorAuth):
    status_code = 403
    titulo = "Cuenta sin verificar"


class AccionInvalida(ErrorAuth):
    status_code = 400
    titulo = "Enlace no válido"


class SesionInvalida(ErrorAuth):
    status_code = 401
    titulo = "Sesión no válida"


class RecursoNoEncontrado(ErrorAuth):
    """Se usa también cuando la cuenta no tiene acceso: así no se revela que el recurso existe (§9.6)."""

    status_code = 404
    titulo = "No encontrado"


class PermisoInsuficiente(ErrorAuth):
    status_code = 403
    titulo = "Permiso insuficiente"


class ReglaNegocio(ErrorAuth):
    status_code = 422
    titulo = "No se puede completar la acción"


class PinIncorrecto(ErrorAuth):
    status_code = 403
    titulo = "PIN incorrecto"


class ConsentimientoRequerido(ErrorAuth):
    status_code = 403
    titulo = "Consentimiento requerido"


class ErrorConfiguracion(Exception):
    """Falta una configuración obligatoria. Es un error del servidor, no del usuario."""
