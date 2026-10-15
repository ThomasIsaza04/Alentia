import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class PerfilIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    fecha_nacimiento: date
    # True para menores o adultos a cargo: el perfil no tiene cuenta propia.
    dependiente: bool = False


class PerfilActualizarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    fecha_nacimiento: date | None = None


class PerfilOut(BaseModel):
    id: uuid.UUID
    nombre: str
    fecha_nacimiento: date
    dependiente: bool
    rol: str
    alcance: str


class ZonaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)


class ZonaActualizarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    archivada: bool | None = None


class ZonaOut(BaseModel):
    id: uuid.UUID
    perfil_id: uuid.UUID
    nombre: str
    archivada: bool


class AccesoOut(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID
    correo: str
    rol: str
    alcance: str
    estado: str
    inicio: datetime


class InvitacionIn(BaseModel):
    correo: EmailStr
    alcance: Literal["lector", "editor", "admin"]


class InvitacionAceptarIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
