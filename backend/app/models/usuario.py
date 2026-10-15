import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc


class Usuario(Base):
    """Cuenta de acceso (documento §10). Separada del perfil de salud (ADR-02)."""

    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    hash_contrasena: Mapped[str] = mapped_column(String(255))
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[str] = mapped_column(String(20), default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    # Bloqueo tras intentos fallidos (RF-AUT-03).
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Eliminación con período de gracia de 7 días (RF-CON-04). Null = no solicitada.
    eliminar_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
