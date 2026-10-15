"""Configuración de la aplicación (12 factores, §12.2). Los secretos viven en el entorno."""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Alentia API"
    app_version: str = "0.3.0"
    environment: str = "development"  # development | staging | production

    # La aplicación se conecta con el rol restringido 'alentia_app'.
    database_url: str = "postgresql+psycopg://alentia_app:cambiar_en_env@localhost:5432/alentia"
    # Las migraciones usan el dueño del esquema. Si no se define, se usa database_url.
    migration_database_url: str | None = None
    test_database_url: str | None = None
    # Misma base de pruebas, conectada como 'alentia_app', para verificar permisos.
    app_test_database_url: str | None = None
    cors_origins: list[str] = ["http://localhost:5173"]
    frontend_url: str = "http://localhost:5173"
    # Zona horaria por defecto para horarios de medicación cuando el cliente no la envía.
    zona_horaria_por_defecto: str = "America/Bogota"
    # Recordatorios: una toma se marca atrasada tras esta ventana y omitida al cumplirse el plazo.
    ventana_atraso_horas: int = 2
    horas_para_omision: int = 12

    # Cifrado en reposo (§7.3)
    encryption_active_key_id: str = "k1"
    encryption_keys: dict[str, str] = {}

    # Autenticación (§7.5, RF-AUT-03). jwt_secret: mínimo 32 caracteres, solo en el entorno.
    jwt_secret: str = ""
    access_token_minutos: int = 15
    refresh_dias: int = 14  # Valor propuesto por el equipo; ajustar con el instructor.

    # Cookie del refresh token. Con dominio compartido (ADR-07) se usa "lax" o "strict".
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"


settings = Settings()
