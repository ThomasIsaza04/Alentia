"""Rol restringido de aplicación: solo adición real en las tablas de auditoría.

Revision ID: 0003_permisos_rol_aplicacion
Revises: 0002_autenticacion
Create Date: 2026-10-13
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003_permisos_rol_aplicacion"
down_revision: str | None = "0002_autenticacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROL = "alentia_app"

# Si el rol no existe (por ejemplo, en una base creada sin db/init), la migración no falla:
# registra un aviso. Sin el rol, la aplicación no podrá conectarse con permisos restringidos.
SQL_CONCEDER = f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROL}') THEN
    RAISE NOTICE 'El rol {ROL} no existe; no se conceden permisos. Crearlo con db/init.';
    RETURN;
  END IF;
  EXECUTE 'GRANT CONNECT ON DATABASE ' || quote_ident(current_database()) || ' TO {ROL}';
  GRANT USAGE ON SCHEMA public TO {ROL};
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROL};
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROL};
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROL};
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROL};
  -- Auditoría: solo adición para la aplicación (además del trigger de la migración 0001).
  REVOKE UPDATE, DELETE ON auditoria FROM {ROL};
  -- Registros de tomas y síntomas: nunca se modifican. El borrado de cuenta (RF-CON-04)
  -- se hará con DELETE autorizado por el trigger, no con UPDATE.
  REVOKE UPDATE ON toma_registro, sintoma_registro FROM {ROL};
  -- Las migraciones de esquema no son tarea de la aplicación.
  REVOKE ALL ON alembic_version FROM {ROL};
END $$;
"""

SQL_RETIRAR = f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROL}') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROL};
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {ROL};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {ROL};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {ROL};
  END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(SQL_CONCEDER)


def downgrade() -> None:
    op.execute(SQL_RETIRAR)
