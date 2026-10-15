"""Tipo de columna cifrada (§7.3).

El valor se cifra con AES-256-GCM antes de llegar a PostgreSQL y se descifra al leerlo.
El contexto (por ejemplo "perfil.nombre") se usa como dato autenticado: un valor
cifrado para una columna no sirve si alguien lo copia a otra.
"""
from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.crypto import cifrar, descifrar


class CampoCifrado(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, contexto: str) -> None:
        super().__init__()
        self.contexto = contexto

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return cifrar(value, self.contexto)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return descifrar(value, self.contexto)
