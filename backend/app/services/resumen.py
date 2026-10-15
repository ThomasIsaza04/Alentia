"""Resumen determinista para el profesional (RF-QRM-06 y RF-QRM-07 no incluido).

Reglas:
- Solo se incluyen las categorías que el paciente eligió al generar el acceso.
- Cada línea lleva la fecha de su registro de origen.
- No hay texto generado por IA: el contenido es el registro tal cual, con una regla de resaltado.
- Sin registros en una categoría, se indica "Sin información registrada".
"""
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Diagnostico, Medicamento, SintomaRegistro, TomaProgramada, TomaRegistro
from app.services.salud import zona_valida

VENTANA_DIAS = 7
DIAS_SEGUIDOS_PARA_DESTACAR = 3

TITULOS = {
    "diagnosticos": "Diagnósticos vigentes",
    "medicamentos": "Medicamentos activos",
    "sintomas": "Síntomas recientes",
}


def _dias_seguidos_maximos(fechas: set[date]) -> int:
    if not fechas:
        return 0
    mejor = actual = 1
    orden = sorted(fechas)
    for anterior, siguiente in zip(orden, orden[1:]):
        actual = actual + 1 if siguiente - anterior == timedelta(days=1) else 1
        mejor = max(mejor, actual)
    return mejor


def construir_resumen(categorias: list[str], datos: dict) -> dict:
    """Función pura: convierte los datos del perfil en líneas con fecha. No inventa contenido."""
    secciones = []
    if "diagnosticos" in categorias:
        lineas = [
            {"texto": d["descripcion"], "fecha": d["fecha"].isoformat(), "destacado": False}
            for d in datos["diagnosticos"]
        ]
        secciones.append(_seccion("diagnosticos", lineas))

    if "medicamentos" in categorias:
        lineas = [
            {"texto": f"{m['nombre']} · {m['dosis']}", "fecha": m["desde"].isoformat(), "destacado": False}
            for m in datos["medicamentos"]
        ]
        adherencia = datos.get("adherencia")
        if adherencia and adherencia["programadas"] > 0:
            lineas.append(
                {
                    "texto": (
                        f"Adherencia de los últimos {VENTANA_DIAS} días: "
                        f"{adherencia['tomadas']} de {adherencia['programadas']} tomas registradas como tomadas"
                    ),
                    "fecha": adherencia["hasta"].isoformat(),
                    "destacado": False,
                }
            )
        secciones.append(_seccion("medicamentos", lineas))

    if "sintomas" in categorias:
        por_sintoma: dict[str, set[date]] = defaultdict(set)
        for s in datos["sintomas"]:
            por_sintoma[s["sintoma"]].add(s["fecha"])
        destacados = {
            nombre
            for nombre, fechas in por_sintoma.items()
            if _dias_seguidos_maximos(fechas) >= DIAS_SEGUIDOS_PARA_DESTACAR
        }
        lineas = [
            {
                "texto": f"{s['sintoma']} · intensidad {s['intensidad']}/10",
                "fecha": s["fecha"].isoformat(),
                "destacado": s["sintoma"] in destacados,
            }
            for s in datos["sintomas"]
        ]
        secciones.append(_seccion("sintomas", lineas))

    return {"categorias": categorias, "secciones": secciones}


def _seccion(clave: str, lineas: list[dict]) -> dict:
    return {
        "clave": clave,
        "titulo": TITULOS[clave],
        "lineas": lineas,
        "sin_informacion": len(lineas) == 0,
    }


def reunir_datos(db: Session, perfil_id: uuid.UUID, ahora: datetime) -> dict:
    zona = zona_valida(settings.zona_horaria_por_defecto)
    hoy = ahora.astimezone(zona).date()
    desde_fecha = hoy - timedelta(days=VENTANA_DIAS - 1)

    diagnosticos = [
        {"descripcion": d.descripcion, "fecha": d.fecha}
        for d in db.scalars(
            select(Diagnostico)
            .where(Diagnostico.perfil_id == perfil_id, Diagnostico.estado == "vigente")
            .order_by(Diagnostico.fecha.desc())
        )
    ]

    medicamentos = [
        {"nombre": m.nombre, "dosis": m.dosis, "desde": m.inicio.astimezone(zona).date()}
        for m in db.scalars(
            select(Medicamento)
            .where(Medicamento.perfil_id == perfil_id, Medicamento.activo.is_(True))
            .order_by(Medicamento.inicio)
        )
    ]

    # Adherencia: tomas ya vencidas en la ventana, y cuántas tienen registro "tomada" como último estado.
    inicio_utc = datetime.combine(desde_fecha, datetime.min.time(), tzinfo=zona).astimezone(ahora.tzinfo)
    tomas = db.execute(
        select(TomaProgramada.id)
        .join(Medicamento, Medicamento.id == TomaProgramada.medicamento_id)
        .where(
            Medicamento.perfil_id == perfil_id,
            Medicamento.activo.is_(True),
            TomaProgramada.programada_en >= inicio_utc,
            TomaProgramada.programada_en < ahora,
        )
    ).scalars().all()
    ultimo: dict[uuid.UUID, str] = {}
    if tomas:
        registros = db.scalars(
            select(TomaRegistro)
            .where(TomaRegistro.toma_programada_id.in_(tomas))
            .order_by(TomaRegistro.registrada_en.desc())
        ).all()
        for r in registros:
            ultimo.setdefault(r.toma_programada_id, r.estado)
    adherencia = {
        "programadas": len(tomas),
        "tomadas": sum(1 for t in tomas if ultimo.get(t) == "tomada"),
        "desde": desde_fecha,
        "hasta": hoy,
    }

    sintomas = [
        {"sintoma": s.sintoma, "intensidad": s.intensidad, "fecha": s.fecha.astimezone(zona).date()}
        for s in db.scalars(
            select(SintomaRegistro)
            .where(SintomaRegistro.perfil_id == perfil_id, SintomaRegistro.fecha >= inicio_utc)
            .order_by(SintomaRegistro.fecha.desc())
        )
    ]

    return {
        "diagnosticos": diagnosticos,
        "medicamentos": medicamentos,
        "adherencia": adherencia,
        "sintomas": sintomas,
    }
