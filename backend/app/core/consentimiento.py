"""Política de tratamiento y finalidades del consentimiento (RF-CON-01 y RF-CON-02).

Cualquier cambio de texto exige una versión nueva: quien aceptó una versión anterior debe volver a aceptar.
"""
import hashlib
import json

VERSION = "2026-10-v1"

FINALIDADES = ("salud", "notificaciones", "qr")
OBLIGATORIA = "salud"

TEXTOS = {
    "salud": (
        "Autorizo a Alentia a guardar y tratar mis datos de salud (medicación, tomas, síntomas y "
        "diagnósticos) para gestionar mi registro. Los datos se cifran en reposo. Puedo exportarlos "
        "o eliminarlos en cualquier momento. Es necesario para usar el registro de salud."
    ),
    "notificaciones": (
        "Autorizo recordatorios de tomas y avisos dentro de la aplicación y en mi calendario. "
        "Puedo retirar esta autorización cuando quiera."
    ),
    "qr": (
        "Autorizo generar accesos temporales por QR y PIN para que un profesional consulte solo las "
        "categorías que yo elija, en modo de lectura y durante un tiempo limitado. Puedo revocar un "
        "acceso en cualquier momento."
    ),
}

HASH_POLITICA = hashlib.sha256(
    json.dumps({"version": VERSION, "textos": TEXTOS}, ensure_ascii=False, sort_keys=True).encode("utf-8")
).hexdigest()
