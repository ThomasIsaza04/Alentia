"""Importa todos los modelos para que Alembic y SQLAlchemy los registren."""
from app.models.acceso_temporal import AccesoTemporal, EventoAccesoTemporal, SesionAccesoTemporal
from app.models.auditoria import Auditoria
from app.models.consentimiento import Consentimiento
from app.models.perfil import AccesoPerfil, InvitacionPerfil, Perfil
from app.models.salud import (
    Diagnostico,
    Medicamento,
    SintomaRegistro,
    TomaProgramada,
    TomaRegistro,
    ZonaConsulta,
)
from app.models.sesion import SesionRefresh, TokenAccion
from app.models.usuario import Usuario

__all__ = [
    "AccesoTemporal",
    "Auditoria",
    "Consentimiento",
    "AccesoPerfil",
    "Diagnostico",
    "EventoAccesoTemporal",
    "InvitacionPerfil",
    "Medicamento",
    "Perfil",
    "SesionAccesoTemporal",
    "SesionRefresh",
    "SintomaRegistro",
    "TokenAccion",
    "TomaProgramada",
    "TomaRegistro",
    "Usuario",
    "ZonaConsulta",
]
