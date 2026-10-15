import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CrearAccesoIn(BaseModel):
    categorias: list[Literal["diagnosticos", "medicamentos", "sintomas"]] = Field(min_length=1, max_length=3)
    duracion_minutos: Literal[15, 30]


class CrearAccesoOut(BaseModel):
    id: uuid.UUID
    categorias: list[str]
    duracion_minutos: int
    vence_en: datetime
    # Se muestra una sola vez. El QR codifica solo la ruta con el token; el PIN va aparte.
    token: str
    pin: str
    enlace_path: str


class AccesoOut(BaseModel):
    id: uuid.UUID
    categorias: list[str]
    duracion_minutos: int
    creado_en: datetime
    vence_en: datetime
    estado: str
    consumido_en: datetime | None
    bloqueado_en: datetime | None
    revocado_en: datetime | None


class EventoOut(BaseModel):
    tipo: str
    ocurrido_en: datetime
    tipo_dispositivo: str


class AbrirIn(BaseModel):
    token: str = Field(min_length=20, max_length=100)


class VerificarIn(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    pin: str = Field(pattern=r"^\d{6}$")


class AbrirOut(BaseModel):
    requiere_pin: bool
    vence_en: datetime


class VerificarOut(BaseModel):
    sesion_token: str
    vence_en: datetime
