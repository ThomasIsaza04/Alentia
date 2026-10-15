"""Tablas de solo adición (§7.7 y §10).

auditoria, toma_registro y sintoma_registro no admiten UPDATE ni DELETE.
Excepción controlada: el borrado definitivo de una cuenta (RF-CON-04) activa la
variable de sesión alentia.permitir_borrado con SET LOCAL. Esa variable solo la
usa el servicio de eliminación de cuentas, dentro de su transacción.
"""

TABLAS_SOLO_ADICION = ("toma_registro", "sintoma_registro", "auditoria")

SQL_FUNCION = """
CREATE OR REPLACE FUNCTION impedir_cambios_solo_adicion() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' AND current_setting('alentia.permitir_borrado', true) = 'on' THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION 'Tabla de solo adicion: no se permiten modificaciones';
END;
$$ LANGUAGE plpgsql;
"""


def sql_crear_triggers() -> list[str]:
    sentencias = [SQL_FUNCION]
    for tabla in TABLAS_SOLO_ADICION:
        sentencias.append(
            f"CREATE TRIGGER {tabla}_solo_adicion BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION impedir_cambios_solo_adicion()"
        )
    return sentencias


def sql_eliminar_triggers() -> list[str]:
    sentencias = [
        f"DROP TRIGGER IF EXISTS {tabla}_solo_adicion ON {tabla}"
        for tabla in TABLAS_SOLO_ADICION
    ]
    sentencias.append("DROP FUNCTION IF EXISTS impedir_cambios_solo_adicion()")
    return sentencias
