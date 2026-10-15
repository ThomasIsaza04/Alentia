"""Base declarativa de SQLAlchemy y utilidades de tiempo."""
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def ahora_utc() -> datetime:
    """Todas las marcas de tiempo se guardan en UTC (RNF19)."""
    return datetime.now(timezone.utc)
