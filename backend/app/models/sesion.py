import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc


class TokenAccion(Base):
    """Token de un solo uso para verificar correo o recuperar contraseña (RF-AUT-02 y RF-AUT-04)."""

    __tablename__ = "token_accion"
    __table_args__ = (
        CheckConstraint("tipo IN ('verificacion','recuperacion')", name="ck_token_accion_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(20))
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SesionRefresh(Base):
    """Refresh token rotativo. 'familia_id' agrupa las rotaciones de una misma sesión (detección de reutilización)."""

    __tablename__ = "sesion_refresh"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    familia_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
