"""Archivo .ics con una alarma por toma (RF-NOT-02). Cada toma es un evento en UTC.

Limitación: se exportan las tomas ya programadas (30 días), no una regla de recurrencia.
Al extender las tomas, se puede volver a descargar el archivo.
"""
from datetime import datetime, timedelta

AVISO = "Este recordatorio no reemplaza la indicación médica y puede fallar."


def _escapar(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")
    )


def _plegar(linea: str) -> list[str]:
    """RFC 5545: las líneas se pliegan a 75 octetos; las continuaciones empiezan con un espacio."""
    octetos = linea.encode("utf-8")
    if len(octetos) <= 75:
        return [linea]
    partes, actual = [], b""
    limite = 75
    for caracter in linea:
        bytes_c = caracter.encode("utf-8")
        if len(actual) + len(bytes_c) > limite:
            partes.append(actual.decode("utf-8"))
            actual = b""
            limite = 74
        actual += bytes_c
    partes.append(actual.decode("utf-8"))
    return [partes[0]] + [" " + p for p in partes[1:]]


def generar(tomas: list[tuple[str, str, str, datetime]], ahora: datetime) -> str:
    """tomas: (uid, nombre, dosis, programada_en en UTC)."""
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Alentia//Recordatorios//ES",
        "CALSCALE:GREGORIAN",
    ]
    sello = ahora.strftime("%Y%m%dT%H%M%SZ")
    for uid, nombre, dosis, programada_en in tomas:
        resumen = f"Tomar {nombre} {dosis}"
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}@alentia",
            f"DTSTAMP:{sello}",
            f"DTSTART:{programada_en.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{(programada_en + timedelta(minutes=15)).strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{_escapar(resumen)}",
            f"DESCRIPTION:{_escapar(AVISO)}",
            "BEGIN:VALARM",
            "TRIGGER:-PT0M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escapar(resumen)}",
            "END:VALARM",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    plegadas = []
    for linea in lineas:
        plegadas.extend(_plegar(linea))
    return "\r\n".join(plegadas) + "\r\n"
