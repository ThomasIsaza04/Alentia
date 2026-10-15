import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

HORA_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


class FrecuenciaHoras(BaseModel):
    tipo: Literal["horarios"]
    horas: list[Annotated[str, Field(pattern=HORA_RE)]] = Field(min_length=1, max_length=12)

    @field_validator("horas")
    @classmethod
    def sin_repetidas(cls, valor: list[str]) -> list[str]:
        if len(set(valor)) != len(valor):
            raise ValueError("Hay horas repetidas")
        return sorted(valor)


class FrecuenciaCadaHoras(BaseModel):
    tipo: Literal["cada_horas"]
    cada_horas: int = Field(ge=1, le=24)
    desde: str = Field(pattern=HORA_RE)


Frecuencia = Annotated[FrecuenciaHoras | FrecuenciaCadaHoras, Field(discriminator="tipo")]


class MedicamentoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    dosis: str = Field(min_length=1, max_length=60)
    frecuencia: Frecuencia
    inicio: date
    fin: date | None = None
    zona_horaria: str = Field(min_length=1, max_length=60)


class MedicamentoActualizarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    dosis: str | None = Field(default=None, min_length=1, max_length=60)
    activo: bool | None = None


class MedicamentoOut(BaseModel):
    id: uuid.UUID
    perfil_id: uuid.UUID
    nombre: str
    dosis: str
    frecuencia: dict
    inicio: datetime
    fin: datetime | None
    activo: bool


class TomaOut(BaseModel):
    id: uuid.UUID
    medicamento_id: uuid.UUID
    nombre: str
    dosis: str
    programada_en: datetime
    fecha_local: str
    hora_local: str
    estado: str | None
    registro_id: uuid.UUID | None


class RegistroTomaIn(BaseModel):
    estado: Literal["tomada", "omitida", "pospuesta"]
    id: uuid.UUID | None = None


class RegistroTomaOut(BaseModel):
    id: uuid.UUID
    toma_id: uuid.UUID
    estado: str
    registrada_en: datetime


class SintomaIn(BaseModel):
    sintoma: str = Field(min_length=1, max_length=100)
    intensidad: int = Field(ge=0, le=10)
    nota: str | None = Field(default=None, max_length=500)
    fecha: datetime | None = None
    id: uuid.UUID | None = None

    @field_validator("fecha")
    @classmethod
    def con_zona_horaria(cls, valor: datetime | None) -> datetime | None:
        if valor is not None and valor.tzinfo is None:
            raise ValueError("La fecha debe incluir la zona horaria")
        return valor


class SintomaOut(BaseModel):
    id: uuid.UUID
    sintoma: str
    intensidad: int
    nota: str | None
    fecha: datetime


class DiagnosticoIn(BaseModel):
    descripcion: str = Field(min_length=1, max_length=500)
    fecha: date
    zona_id: uuid.UUID | None = None
    estado: Literal["vigente", "resuelto"] = "vigente"


class DiagnosticoEstadoIn(BaseModel):
    descripcion: str | None = Field(default=None, min_length=1, max_length=500)
    estado: Literal["vigente", "resuelto"] | None = None


class DiagnosticoOut(BaseModel):
    id: uuid.UUID
    descripcion: str
    fecha: date
    estado: str
    zona_id: uuid.UUID | None
