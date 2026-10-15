"""Acceso temporal del profesional por QR y PIN (RF-QRM-01 a RF-QRM-05)."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc


class AccesoTemporal(Base):
    """Un QR emitido. Solo se guarda el hash del token y el hash del PIN."""

    __tablename__ = "acceso_temporal"
    __table_args__ = (
        CheckConstraint("duracion_minutos IN (15, 30)", name="ck_acceso_temporal_duracion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"), index=True)
    creado_por: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id", ondelete="CASCADE"))
    # Categorías compartidas, separadas por coma. No contienen datos personales.
    categorias: Mapped[str] = mapped_column(String(200))
    duracion_minutos: Mapped[int] = mapped_column(SmallInteger)
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    hash_pin: Mapped[str] = mapped_column(String(200))
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bloqueado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SesionAccesoTemporal(Base):
    """Sesión de solo lectura del profesional. Se crea al consumir el acceso."""

    __tablename__ = "sesion_acceso_temporal"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    acceso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("acceso_temporal.id", ondelete="CASCADE"), index=True
    )
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventoAccesoTemporal(Base):
    """Bitácora de solo adición (RF-QRM-05). No incluye datos personales del profesional."""

    __tablename__ = "evento_acceso_temporal"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('generado','abierto','pin_fallido','bloqueado','consumido','revocado')",
            name="ck_evento_acceso_tipo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    acceso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("acceso_temporal.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(20))
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    tipo_dispositivo: Mapped[str] = mapped_column(String(20), default="desconocido")
