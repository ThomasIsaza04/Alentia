"""Ejecuta una vez las tareas de mantenimiento: extensión de tomas, omisiones y purga de cuentas.

Uso:  python -m app.tareas.ejecutar
Programarla cada hora (cron o el planificador del entorno de despliegue). Es idempotente:
ejecutarla varias veces no duplica tomas ni registros.
"""
from app.db.session import SessionLocal
from app.services.tareas import ejecutar_todas


def main() -> dict[str, int]:
    with SessionLocal() as db:
        resultado = ejecutar_todas(db)
    for clave, valor in resultado.items():
        print(f"{clave}: {valor}")
    return resultado


if __name__ == "__main__":
    main()
