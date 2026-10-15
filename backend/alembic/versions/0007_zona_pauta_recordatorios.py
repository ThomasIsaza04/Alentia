"""Zona horaria por pauta (paso 9): la extensión de tomas necesita la zona en la que se escribió la pauta.

Revision ID: 0007_zona_pauta_recordatorios
Revises: 0006_consentimiento_eliminacion
Create Date: 2026-10-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_zona_pauta_recordatorios"
down_revision: str | None = "0006_consentimiento_eliminacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "medicamento",
        sa.Column("zona_horaria", sa.String(60), nullable=False, server_default="America/Bogota"),
    )


def downgrade() -> None:
    op.drop_column("medicamento", "zona_horaria")
