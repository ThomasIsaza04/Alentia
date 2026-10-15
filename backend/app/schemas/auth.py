import uuid

from pydantic import BaseModel, EmailStr, Field


class RegistroIn(BaseModel):
    correo: EmailStr
    clave: str = Field(min_length=1, max_length=128)


class CorreoIn(BaseModel):
    correo: EmailStr


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class LoginIn(BaseModel):
    correo: EmailStr
    clave: str = Field(min_length=1, max_length=128)


class RestablecerIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    clave: str = Field(min_length=1, max_length=128)


class AccesoOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MensajeOut(BaseModel):
    mensaje: str


class UsuarioOut(BaseModel):
    id: uuid.UUID
    correo: str
    verificado: bool
