"""Configuración común de pruebas.

- Llaves de cifrado y de JWT de prueba (nunca reales).
- Motor PostgreSQL con migraciones aplicadas. Si TEST_DATABASE_URL no está definida, las pruebas de BD se omiten.
"""
import base64
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def llaves_de_prueba(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "encryption_keys", {"k1": base64.b64encode(b"0" * 32).decode()})
    monkeypatch.setattr(settings, "encryption_active_key_id", "k1")
    monkeypatch.setattr(settings, "jwt_secret", "secreto-de-prueba-de-al-menos-32-caracteres")


@pytest.fixture(scope="session")
def engine():
    url = settings.test_database_url
    if not url:
        pytest.skip("Definir TEST_DATABASE_URL para ejecutar pruebas de base de datos")

    # Las pruebas usan una base aparte. Se verifica el nombre para no borrar una base de trabajo por error.
    if "test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base cuyo nombre contenga 'test'")
    anterior = settings.database_url
    anterior_migracion = settings.migration_database_url
    settings.database_url = url
    settings.migration_database_url = url
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    motor = create_engine(url)
    yield motor
    motor.dispose()
    command.downgrade(cfg, "base")
    settings.database_url = anterior
    settings.migration_database_url = anterior_migracion


@pytest.fixture
def session(engine):
    with Session(engine) as sesion:
        yield sesion
        sesion.rollback()
