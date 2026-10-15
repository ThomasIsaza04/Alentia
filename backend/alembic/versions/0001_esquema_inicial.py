"""Esquema inicial de Alentia: cuentas, perfiles, salud, medicación, síntomas y auditoría.

Revision ID: 0001_esquema_inicial
Revises:
Create Date: 2026-10-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.triggers import sql_crear_triggers, sql_eliminar_triggers

revision: str = "0001_esquema_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("hash_contrasena", sa.String(255), nullable=False),
        sa.Column("verificado", sa.Boolean(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correo"),
    )

    op.create_table(
        "perfil",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=False),
        sa.Column("titular_usuario_id", sa.Uuid(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["titular_usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "acceso_perfil",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("alcance", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rol IN ('titular','representante','cuidador')", name="ck_acceso_perfil_rol"),
        sa.CheckConstraint("alcance IN ('lector','editor','admin')", name="ck_acceso_perfil_alcance"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "perfil_id", name="uq_acceso_usuario_perfil"),
    )

    op.create_table(
        "zona_consulta",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("archivada", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "diagnostico",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("zona_id", sa.Uuid(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.CheckConstraint("estado IN ('vigente','resuelto')", name="ck_diagnostico_estado"),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zona_id"], ["zona_consulta.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "medicamento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("dosis", sa.Text(), nullable=False),
        sa.Column("frecuencia", sa.Text(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "toma_programada",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("medicamento_id", sa.Uuid(), nullable=False),
        sa.Column("programada_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["medicamento_id"], ["medicamento.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("medicamento_id", "programada_en", name="uq_toma_medicamento_hora"),
    )

    op.create_table(
        "toma_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("toma_programada_id", sa.Uuid(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrada_por", sa.Uuid(), nullable=True),
        sa.CheckConstraint("estado IN ('tomada','omitida','pospuesta')", name="ck_toma_registro_estado"),
        sa.ForeignKeyConstraint(["toma_programada_id"], ["toma_programada.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sintoma_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("sintoma", sa.String(100), nullable=False),
        sa.Column("intensidad", sa.SmallInteger(), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.Uuid(), nullable=True),
        sa.CheckConstraint("intensidad BETWEEN 0 AND 10", name="ck_sintoma_registro_intensidad"),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("actor_usuario_id", sa.Uuid(), nullable=True),
        sa.Column("perfil_id", sa.Uuid(), nullable=True),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo_dispositivo", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    for sentencia in sql_crear_triggers():
        op.execute(sentencia)


def downgrade() -> None:
    for sentencia in sql_eliminar_triggers():
        op.execute(sentencia)
    for tabla in (
        "auditoria",
        "sintoma_registro",
        "toma_registro",
        "toma_programada",
        "medicamento",
        "diagnostico",
        "zona_consulta",
        "acceso_perfil",
        "perfil",
        "usuario",
    ):
        op.drop_table(tabla)
