"""Envío de correo. En desarrollo guarda los mensajes en memoria.

En producción debe sustituirse por el envío SMTP de Brevo (nivel gratuito, §9.2).
Esta clase se niega a funcionar en producción para no mostrar enlaces en consola.
"""
from dataclasses import dataclass

from app.core.config import settings
from app.core.errores import ErrorConfiguracion


@dataclass(frozen=True)
class MensajeCorreo:
    destinatario: str
    asunto: str
    cuerpo: str


class CorreoConsola:
    def __init__(self) -> None:
        self.bandeja: list[MensajeCorreo] = []

    def enviar(self, mensaje: MensajeCorreo) -> None:
        if settings.environment == "production":
            raise ErrorConfiguracion("CorreoConsola no puede usarse en producción")
        self.bandeja.append(mensaje)
        if settings.environment == "development":
            # Solo en desarrollo, con datos sintéticos, para poder probar el flujo a mano.
            print(f"[correo de desarrollo] para {mensaje.destinatario}: {mensaje.cuerpo}")

    def ultimo_para(self, destinatario: str) -> MensajeCorreo | None:
        for mensaje in reversed(self.bandeja):
            if mensaje.destinatario == destinatario:
                return mensaje
        return None


remitente = CorreoConsola()
