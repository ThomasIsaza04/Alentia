"""Pruebas del cifrado AES-256-GCM (§7.3)."""
import base64

import pytest

from app.core.config import settings
from app.core.crypto import ErrorCifrado, cifrar, descifrar


def test_ida_y_vuelta() -> None:
    assert descifrar(cifrar("Dolor de cabeza", "sintoma.nota"), "sintoma.nota") == "Dolor de cabeza"


def test_el_texto_no_aparece_en_claro() -> None:
    cifrado = cifrar("Diabetes tipo 2", "diagnostico.descripcion")
    assert "Diabetes" not in cifrado


def test_cada_cifrado_usa_nonce_distinto() -> None:
    assert cifrar("mismo texto", "contexto") != cifrar("mismo texto", "contexto")


def test_contexto_incorrecto_falla() -> None:
    cifrado = cifrar("María Pérez", "perfil.nombre")
    with pytest.raises(ErrorCifrado):
        descifrar(cifrado, "medicamento.nombre")


def test_dato_alterado_falla() -> None:
    version, kid, cuerpo = cifrar("Ibuprofeno 400 mg", "medicamento.dosis").split(":", 2)
    datos = bytearray(base64.b64decode(cuerpo))
    datos[-1] ^= 0x01
    alterado = f"{version}:{kid}:{base64.b64encode(bytes(datos)).decode()}"
    with pytest.raises(ErrorCifrado):
        descifrar(alterado, "medicamento.dosis")


def test_error_no_expone_el_texto() -> None:
    version, kid, cuerpo = cifrar("Ibuprofeno 400 mg", "ctx").split(":", 2)
    datos = bytearray(base64.b64decode(cuerpo))
    datos[-1] ^= 0x01
    alterado = f"{version}:{kid}:{base64.b64encode(bytes(datos)).decode()}"
    with pytest.raises(ErrorCifrado) as error:
        descifrar(alterado, "ctx")
    assert "Ibuprofeno" not in str(error.value)


def test_rotacion_de_llaves(monkeypatch: pytest.MonkeyPatch) -> None:
    llave_original = settings.encryption_keys["k1"]
    cifrado_viejo = cifrar("texto antiguo", "ctx")

    monkeypatch.setattr(
        settings,
        "encryption_keys",
        {"k1": llave_original, "k2": base64.b64encode(b"1" * 32).decode()},
    )
    monkeypatch.setattr(settings, "encryption_active_key_id", "k2")

    assert descifrar(cifrado_viejo, "ctx") == "texto antiguo"
    nuevo = cifrar("texto nuevo", "ctx")
    assert nuevo.startswith("v1:k2:")
    assert descifrar(nuevo, "ctx") == "texto nuevo"


def test_llave_activa_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "encryption_active_key_id", "k9")
    with pytest.raises(ErrorCifrado):
        cifrar("x", "ctx")
