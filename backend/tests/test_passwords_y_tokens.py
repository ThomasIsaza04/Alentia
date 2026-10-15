"""Pruebas unitarias de contraseñas y tokens (no requieren base de datos)."""
import uuid

import pytest

from app.core import passwords
from app.core.config import settings
from app.core.errores import ContrasenaDebil, ErrorConfiguracion
from app.core.tokens import (
    crear_access_token,
    hash_token,
    leer_access_token,
    token_aleatorio,
)


def test_hash_argon2id_y_verificacion() -> None:
    h = passwords.hashear("Clave-segura-2026")
    assert h.startswith("$argon2id$")
    assert passwords.verificar("Clave-segura-2026", h)
    assert not passwords.verificar("otra-clave-distinta", h)


def test_politica_rechaza_clave_corta() -> None:
    with pytest.raises(ContrasenaDebil):
        passwords.validar_politica("corta1")


def test_politica_rechaza_clave_comun() -> None:
    with pytest.raises(ContrasenaDebil):
        passwords.validar_politica("password123")


def test_politica_acepta_clave_valida() -> None:
    passwords.validar_politica("Clave-segura-2026")


def test_access_token_ida_y_vuelta() -> None:
    usuario_id = uuid.uuid4()
    assert leer_access_token(crear_access_token(usuario_id)) == usuario_id


def test_access_token_expirado_no_sirve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "access_token_minutos", -1)
    assert leer_access_token(crear_access_token(uuid.uuid4())) is None


def test_access_token_alterado_no_sirve() -> None:
    token = crear_access_token(uuid.uuid4())
    alterado = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert leer_access_token(alterado) is None


def test_sin_jwt_secret_falla_con_error_de_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "corto")
    with pytest.raises(ErrorConfiguracion):
        crear_access_token(uuid.uuid4())


def test_tokens_opacos_son_unicos_y_se_guardan_con_hash() -> None:
    t1, t2 = token_aleatorio(), token_aleatorio()
    assert t1 != t2
    assert len(t1) >= 43  # 32 bytes en base64url
    assert hash_token(t1) != t1
    assert len(hash_token(t1)) == 64
