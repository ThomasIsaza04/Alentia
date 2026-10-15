import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc


class Auditoria(Base):
    """Bitácora de solo adición (§7.7). No guarda contenido de salud.

    No tiene claves foráneas: así sobrevive a la eliminación de la cuenta sin datos identificables.
    """

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    actor_usuario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    perfil_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    accion: Mapped[str] = mapped_column(String(50))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    tipo_dispositivo: Mapped[str | None] = mapped_column(String(20), nullable=True)
