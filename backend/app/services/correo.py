"""Envío de correo.

- En desarrollo y pruebas: CorreoConsola guarda los mensajes en memoria.
- En producción: CorreoSMTP envía por el servidor SMTP de Brevo (nivel gratuito, §9.2).
  Si faltan credenciales, la aplicación no arranca: es preferible un error claro a un fallo al registrarse.
"""
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

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


class CorreoSMTP:
    def __init__(self, host: str, puerto: int, usuario: str, clave: str, remitente: str) -> None:
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.clave = clave
        self.remitente = remitente

    def enviar(self, mensaje: MensajeCorreo) -> None:
        email = EmailMessage()
        email["From"] = self.remitente
        email["To"] = mensaje.destinatario
        email["Subject"] = mensaje.asunto
        email.set_content(mensaje.cuerpo)
        contexto = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.puerto, timeout=15) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(self.usuario, self.clave)
            servidor.send_message(email)


def _crear_remitente() -> CorreoConsola | CorreoSMTP:
    if settings.environment != "production":
        return CorreoConsola()
    faltantes = [
        nombre
        for nombre, valor in [
            ("SMTP_USUARIO", settings.smtp_usuario),
            ("SMTP_CLAVE", settings.smtp_clave),
            ("CORREO_REMITENTE", settings.correo_remitente),
        ]
        if not valor
    ]
    if faltantes:
        raise ErrorConfiguracion(f"Faltan variables de correo en producción: {', '.join(faltantes)}")
    return CorreoSMTP(
        host=settings.smtp_host,
        puerto=settings.smtp_port,
        usuario=settings.smtp_usuario,
        clave=settings.smtp_clave,
        remitente=settings.correo_remitente,
    )


remitente = _crear_remitente()