from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConsentimientoIn(BaseModel):
    finalidad: Literal["salud", "notificaciones", "qr"]
    version: str = Field(min_length=1, max_length=20)
    aceptado: bool


class EliminacionIn(BaseModel):
    clave: str = Field(min_length=1, max_length=200)


class EliminacionOut(BaseModel):
    eliminar_en: datetime | None
