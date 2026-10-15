import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc
from app.db.types import CampoCifrado


class ZonaConsulta(Base):
    """Categoría para agrupar registros (cardiología, pediatría...)."""

    __tablename__ = "zona_consulta"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(CampoCifrado("zona_consulta.nombre"))
    archivada: Mapped[bool] = mapped_column(Boolean, default=False)


class Diagnostico(Base):
    __tablename__ = "diagnostico"
    __table_args__ = (
        CheckConstraint("estado IN ('vigente','resuelto')", name="ck_diagnostico_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"))
    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("zona_consulta.id", ondelete="SET NULL"), nullable=True
    )
    descripcion: Mapped[str] = mapped_column(CampoCifrado("diagnostico.descripcion"))
    fecha: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="vigente")


class Medicamento(Base):
    """Pauta de medicación. Nombre, dosis y frecuencia van cifrados (§7.3)."""

    __tablename__ = "medicamento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(CampoCifrado("medicamento.nombre"))
    dosis: Mapped[str] = mapped_column(CampoCifrado("medicamento.dosis"))
    # Frecuencia serializada en JSON (cada N horas, horarios fijos o días específicos).
    frecuencia: Mapped[str] = mapped_column(CampoCifrado("medicamento.frecuencia"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Zona en la que se escribió la pauta. La extensión de tomas la necesita para respetar la hora local.
    zona_horaria: Mapped[str] = mapped_column(String(60), default="America/Bogota", server_default="America/Bogota")


class TomaProgramada(Base):
    """Toma calculada a partir de la pauta. Se guarda en UTC."""

    __tablename__ = "toma_programada"
    __table_args__ = (
        UniqueConstraint("medicamento_id", "programada_en", name="uq_toma_medicamento_hora"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    medicamento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("medicamento.id", ondelete="CASCADE")
    )
    programada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TomaRegistro(Base):
    """Registro real de una toma. Solo adición. El id lo genera el cliente (sin duplicados offline)."""

    __tablename__ = "toma_registro"
    __table_args__ = (
        CheckConstraint("estado IN ('tomada','omitida','pospuesta')", name="ck_toma_registro_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    toma_programada_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("toma_programada.id", ondelete="CASCADE")
    )
    estado: Mapped[str] = mapped_column(String(20))
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    # Sin clave foránea: el registro debe conservarse aunque la cuenta se elimine.
    registrada_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class SintomaRegistro(Base):
    """Registro diario de síntomas. Solo adición (§10)."""

    __tablename__ = "sintoma_registro"
    __table_args__ = (
        CheckConstraint("intensidad BETWEEN 0 AND 10", name="ck_sintoma_registro_intensidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"))
    sintoma: Mapped[str] = mapped_column(String(100))
    intensidad: Mapped[int] = mapped_column(SmallInteger)
    nota: Mapped[str | None] = mapped_column(CampoCifrado("sintoma.nota"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registrado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
