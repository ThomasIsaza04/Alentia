#!/bin/sh
# Se ejecuta una sola vez, al crear el volumen de PostgreSQL (docker-entrypoint-initdb.d).
# Crea el rol restringido con el que la API se conecta. Las migraciones usan el dueño (POSTGRES_USER).
set -e

if [ -z "$APP_DB_PASSWORD" ]; then
  echo "Falta APP_DB_PASSWORD en el entorno de la base de datos" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alentia_app') THEN
      CREATE ROLE alentia_app LOGIN PASSWORD '$APP_DB_PASSWORD' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
  END
  \$\$;
EOSQL
