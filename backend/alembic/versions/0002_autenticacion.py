"""Autenticación: bloqueo de cuentas, tokens de acción y sesiones de refresh.

Revision ID: 0002_autenticacion
Revises: 0001_esquema_inicial
Create Date: 2026-10-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_autenticacion"
down_revision: str | None = "0001_esquema_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("intentos_fallidos", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("usuario", sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "token_accion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tipo IN ('verificacion','recuperacion')", name="ck_token_accion_tipo"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash_token"),
    )
    op.create_index("ix_token_accion_usuario_id", "token_accion", ["usuario_id"], unique=False)

    op.create_table(
        "sesion_refresh",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("familia_id", sa.Uuid(), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocada", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash_token"),
    )
    op.create_index("ix_sesion_refresh_usuario_id", "sesion_refresh", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sesion_refresh_usuario_id", table_name="sesion_refresh")
    op.drop_table("sesion_refresh")
    op.drop_index("ix_token_accion_usuario_id", table_name="token_accion")
    op.drop_table("token_accion")
    op.drop_column("usuario", "bloqueado_hasta")
    op.drop_column("usuario", "intentos_fallidos")
