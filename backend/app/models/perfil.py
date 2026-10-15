import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base, ahora_utc
from app.db.types import CampoCifrado


class Perfil(Base):
    """Persona cuya salud se registra. Puede no tener cuenta propia (menores, adultos mayores)."""

    __tablename__ = "perfil"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(CampoCifrado("perfil.nombre"))
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    # Nulo si el perfil es dependiente (menor o adulto a cargo de un cuidador).
    titular_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)


class AccesoPerfil(Base):
    """Vínculo entre una cuenta y un perfil, con rol y alcance (§4.2)."""

    __tablename__ = "acceso_perfil"
    __table_args__ = (
        UniqueConstraint("usuario_id", "perfil_id", name="uq_acceso_usuario_perfil"),
        CheckConstraint("rol IN ('titular','representante','cuidador')", name="ck_acceso_perfil_rol"),
        CheckConstraint("alcance IN ('lector','editor','admin')", name="ck_acceso_perfil_alcance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id", ondelete="CASCADE"))
    perfil_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("perfil.id", ondelete="CASCADE"))
    rol: Mapped[str] = mapped_column(String(20))
    alcance: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), default="activo")
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InvitacionPerfil(Base):
    """Invitación para vincular otra cuenta a un perfil. El token en claro nunca se guarda (solo su hash)."""

    __tablename__ = "invitacion_perfil"
    __table_args__ = (
        CheckConstraint("alcance IN ('lector','editor','admin')", name="ck_invitacion_alcance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    perfil_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("perfil.id", ondelete="CASCADE"), index=True
    )
    correo_invitado: Mapped[str] = mapped_column(String(254))
    alcance: Mapped[str] = mapped_column(String(20))
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    creada_por: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id", ondelete="CASCADE"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    aceptada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
