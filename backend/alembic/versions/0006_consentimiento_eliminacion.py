"""Consentimiento por finalidad y eliminación de cuenta con período de gracia (paso 8).

Revision ID: 0006_consentimiento_eliminacion
Revises: 0005_acceso_temporal
Create Date: 2026-10-13

- Tabla consentimiento: solo adición (cada aceptación o retiro es una fila nueva).
- usuario.eliminar_en: fecha en que se eliminará la cuenta, si el titular la solicitó.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_consentimiento_eliminacion"
down_revision: str | None = "0005_acceso_temporal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuario", sa.Column("eliminar_en", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "consentimiento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("finalidad", sa.String(20), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("hash_politica", sa.String(64), nullable=False),
        sa.Column("aceptado", sa.Boolean(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("finalidad IN ('salud','notificaciones','qr')", name="ck_consentimiento_finalidad"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consentimiento_usuario_id", "consentimiento", ["usuario_id"])
    op.execute(
        "CREATE TRIGGER consentimiento_solo_adicion BEFORE UPDATE OR DELETE ON consentimiento "
        "FOR EACH ROW EXECUTE FUNCTION impedir_cambios_solo_adicion()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS consentimiento_solo_adicion ON consentimiento")
    op.drop_table("consentimiento")
    op.drop_column("usuario", "eliminar_en")
