"""Elimina definitivamente las cuentas cuyo período de gracia venció.

Uso:  python -m app.tareas.purgar_cuentas
La tarea programada del paso 9 la ejecutará cada día.
"""
from app.db.base import ahora_utc
from app.db.session import SessionLocal
from app.services.cuenta import eliminar_vencidas


def main() -> int:
    with SessionLocal() as db:
        total = eliminar_vencidas(db, ahora_utc())
    print(f"Cuentas eliminadas: {total}")
    return total


if __name__ == "__main__":
    main()
