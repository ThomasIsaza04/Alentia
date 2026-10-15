"""Acceso temporal del profesional por QR y PIN (paso 7).

Revision ID: 0005_acceso_temporal
Revises: 0004_perfiles_zonas_invitaciones
Create Date: 2026-10-13

Tablas nuevas: acceso_temporal, sesion_acceso_temporal y evento_acceso_temporal.
La bitácora (evento_acceso_temporal) es de solo adición, igual que auditoria.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_acceso_temporal"
down_revision: str | None = "0004_perfiles_zonas_invitaciones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SQL_SOLO_ADICION = """
CREATE TRIGGER evento_acceso_temporal_solo_adicion BEFORE UPDATE OR DELETE ON evento_acceso_temporal
FOR EACH ROW EXECUTE FUNCTION impedir_cambios_solo_adicion();
"""


def upgrade() -> None:
    op.create_table(
        "acceso_temporal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("creado_por", sa.Uuid(), nullable=False),
        sa.Column("categorias", sa.String(200), nullable=False),
        sa.Column("duracion_minutos", sa.SmallInteger(), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("hash_pin", sa.String(200), nullable=False),
        sa.Column("intentos_fallidos", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bloqueado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("duracion_minutos IN (15, 30)", name="ck_acceso_temporal_duracion"),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash_token"),
    )
    op.create_index("ix_acceso_temporal_perfil_id", "acceso_temporal", ["perfil_id"])

    op.create_table(
        "sesion_acceso_temporal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("acceso_id", sa.Uuid(), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["acceso_id"], ["acceso_temporal.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash_token"),
    )
    op.create_index("ix_sesion_acceso_temporal_acceso_id", "sesion_acceso_temporal", ["acceso_id"])

    op.create_table(
        "evento_acceso_temporal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("acceso_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo_dispositivo", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('generado','abierto','pin_fallido','bloqueado','consumido','revocado')",
            name="ck_evento_acceso_tipo",
        ),
        sa.ForeignKeyConstraint(["acceso_id"], ["acceso_temporal.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evento_acceso_temporal_acceso_id", "evento_acceso_temporal", ["acceso_id"])
    op.execute(SQL_SOLO_ADICION)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS evento_acceso_temporal_solo_adicion ON evento_acceso_temporal")
    op.drop_table("evento_acceso_temporal")
    op.drop_table("sesion_acceso_temporal")
    op.drop_table("acceso_temporal")
