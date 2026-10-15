"""Perfiles, zonas de consulta cifradas e invitaciones.

Revision ID: 0004_perfiles_zonas_invitaciones
Revises: 0003_permisos_rol_aplicacion
Create Date: 2026-10-13

Cambios:
- zona_consulta.nombre pasa de VARCHAR(100) a TEXT porque ahora se guarda cifrado (§7.3).
  Solo se permite si la tabla está vacía: un valor en claro no se puede descifrar después.
- Nueva tabla invitacion_perfil. Guarda solo el hash del token.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_perfiles_zonas_invitaciones"
down_revision: str | None = "0003_permisos_rol_aplicacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _exigir_tabla_vacia() -> None:
    filas = op.get_bind().execute(sa.text("SELECT count(*) FROM zona_consulta")).scalar_one()
    if filas:
        raise RuntimeError(
            "zona_consulta tiene datos en claro: migrar sus nombres a cifrado antes de continuar"
        )


def upgrade() -> None:
    _exigir_tabla_vacia()
    op.alter_column(
        "zona_consulta",
        "nombre",
        existing_type=sa.String(100),
        type_=sa.Text(),
        existing_nullable=False,
    )

    op.create_table(
        "invitacion_perfil",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("correo_invitado", sa.String(254), nullable=False),
        sa.Column("alcance", sa.String(20), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("creada_por", sa.Uuid(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aceptada_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("alcance IN ('lector','editor','admin')", name="ck_invitacion_alcance"),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creada_por"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash_token"),
    )
    op.create_index("ix_invitacion_perfil_perfil_id", "invitacion_perfil", ["perfil_id"], unique=False)


def downgrade() -> None:
    # Los nombres de zona ya cifrados no se pueden devolver a texto en claro desde SQL, así que
    # la columna se queda en TEXT (compatible hacia atrás). Solo se elimina la tabla nueva.
    op.drop_index("ix_invitacion_perfil_perfil_id", table_name="invitacion_perfil")
    op.drop_table("invitacion_perfil")
