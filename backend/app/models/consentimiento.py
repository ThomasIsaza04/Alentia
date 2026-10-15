import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc


class Consentimiento(Base):
    """Cada aceptación o retiro es una fila nueva (solo adición). El último registro por finalidad manda."""

    __tablename__ = "consentimiento"
    __table_args__ = (
        CheckConstraint("finalidad IN ('salud','notificaciones','qr')", name="ck_consentimiento_finalidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    finalidad: Mapped[str] = mapped_column(String(20))
    version: Mapped[str] = mapped_column(String(20))
    hash_politica: Mapped[str] = mapped_column(String(64))
    aceptado: Mapped[bool] = mapped_column(Boolean)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
