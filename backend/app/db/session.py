"""Motor y sesiones de base de datos."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _desactivar_preparadas(dbapi_connection, _registro):
    # El pooler de transacciones de Supabase (puerto 6543) no admite sentencias preparadas
    # del servidor. Desactivarlas no cambia el comportamiento; solo evita errores intermitentes.
    dbapi_connection.prepare_threshold = None
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
