"""Pruebas de medicación, tomas, síntomas y diagnósticos contra PostgreSQL real (pasos 5 y 6)."""
import uuid
from datetime import date, time
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.db.session import get_db
from app.main import app
from app.models import Medicamento, TomaProgramada, TomaRegistro, Usuario, ZonaConsulta
from app.services import salud as servicio
from tests.test_perfiles_api import (
    BASE,
    cabecera,
    crear_perfil_de,
    crear_usuario,
    dar_acceso,
)

BOGOTA = "America/Bogota"
INICIO = "2026-10-01"


@pytest.fixture
def cliente(session):
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def _medicamento(cliente: TestClient, titular: Usuario, perfil_id: str, **cambios) -> dict:
    cuerpo = {
        "nombre": "Losartán",
        "dosis": "50 mg",
        "frecuencia": {"tipo": "horarios", "horas": ["08:00", "20:00"]},
        "inicio": INICIO,
        "fin": None,
        "zona_horaria": BOGOTA,
    }
    cuerpo.update(cambios)
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/medicamentos", json=cuerpo, headers=cabecera(titular))
    assert r.status_code == 201, r.text
    return r.json()


def _tomas(cliente: TestClient, usuario: Usuario, perfil_id: str, desde: str, hasta: str, zona: str = BOGOTA):
    return cliente.get(
        f"{BASE}/perfiles/{perfil_id}/tomas",
        params={"desde": desde, "hasta": hasta, "zona_horaria": zona},
        headers=cabecera(usuario),
    )


# ---------- reglas puras ----------

def test_horas_fijas_se_ordenan():
    assert servicio.horas_del_dia({"tipo": "horarios", "horas": ["20:00", "08:00"]}) == [
        time(8, 0),
        time(20, 0),
    ]


def test_cada_n_horas_desde_una_hora_inicial():
    horas = servicio.horas_del_dia({"tipo": "cada_horas", "cada_horas": 8, "desde": "06:00"})
    assert horas == [time(6, 0), time(14, 0), time(22, 0)]


def test_cada_horas_sin_pasar_de_medianoche():
    horas = servicio.horas_del_dia({"tipo": "cada_horas", "cada_horas": 12, "desde": "18:00"})
    assert horas == [time(18, 0)]


# ---------- medicación y programación ----------

def test_pauta_genera_tomas_30_dias_en_utc(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id)

    total = session.scalar(
        select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))
    )
    assert total == 60  # 2 tomas diarias × 30 días

    primera = session.scalar(
        select(TomaProgramada.programada_en)
        .where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))
        .order_by(TomaProgramada.programada_en)
    )
    # 08:00 en Bogotá (UTC-5) es 13:00 UTC.
    assert primera.utcoffset().total_seconds() == 0
    assert (primera.year, primera.month, primera.day, primera.hour) == (2026, 10, 1, 13)


def test_listado_muestra_horas_en_zona_del_cliente(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)

    r = _tomas(cliente, titular, perfil_id, INICIO, INICIO, BOGOTA)
    assert r.status_code == 200, r.text
    assert [t["hora_local"] for t in r.json()] == ["08:00", "20:00"]
    assert all(t["fecha_local"] == INICIO and t["estado"] in (None, "atrasada") for t in r.json())

    # Las mismas tomas vistas desde Madrid (UTC+2 en octubre): 08:00 Bogotá = 15:00 Madrid.
    r_madrid = _tomas(cliente, titular, perfil_id, INICIO, INICIO, "Europe/Madrid")
    assert [t["hora_local"] for t in r_madrid.json()] == ["15:00"]


def test_reprogramar_no_duplica_tomas(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id)
    medicamento = session.get(Medicamento, uuid.UUID(med["id"]))
    antes = session.scalar(select(func.count()).select_from(TomaProgramada))

    servicio.programar_tomas(
        session, medicamento, ZoneInfo(BOGOTA), {"tipo": "horarios", "horas": ["08:00", "20:00"]},
        date(2026, 10, 1), None,
    )
    session.commit()
    assert session.scalar(select(func.count()).select_from(TomaProgramada)) == antes


def test_cada_horas_genera_tres_tomas_diarias(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(
        cliente, titular, perfil_id,
        frecuencia={"tipo": "cada_horas", "cada_horas": 8, "desde": "06:00"},
    )
    total = session.scalar(
        select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))
    )
    assert total == 90
    r = _tomas(cliente, titular, perfil_id, INICIO, INICIO)
    assert [t["hora_local"] for t in r.json()] == ["06:00", "14:00", "22:00"]


def test_fin_limita_la_programacion(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id, fin="2026-10-03")
    total = session.scalar(
        select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))
    )
    assert total == 6  # 3 días × 2 tomas


def test_fin_anterior_al_inicio_es_regla_de_negocio(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/medicamentos",
        json={
            "nombre": "X", "dosis": "1", "frecuencia": {"tipo": "horarios", "horas": ["08:00"]},
            "inicio": INICIO, "fin": "2026-09-01", "zona_horaria": BOGOTA,
        },
        headers=cabecera(titular),
    )
    assert r.status_code == 422


def test_zona_horaria_invalida_responde_422(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/medicamentos",
        json={
            "nombre": "X", "dosis": "1", "frecuencia": {"tipo": "horarios", "horas": ["08:00"]},
            "inicio": INICIO, "zona_horaria": "Marte/Olympus",
        },
        headers=cabecera(titular),
    )
    assert r.status_code == 422
    r_tomas = _tomas(cliente, titular, perfil_id, INICIO, INICIO, "Marte/Olympus")
    assert r_tomas.status_code == 422


def test_rango_de_consulta_mayor_a_62_dias_se_rechaza(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = _tomas(cliente, titular, perfil_id, "2026-01-01", "2026-12-31")
    assert r.status_code == 422


def test_desactivar_medicamento_oculta_sus_tomas(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id)
    r = cliente.patch(f"{BASE}/medicamentos/{med['id']}", json={"activo": False}, headers=cabecera(titular))
    assert r.status_code == 200 and r.json()["activo"] is False
    assert _tomas(cliente, titular, perfil_id, INICIO, INICIO).json() == []


def test_nombre_y_dosis_se_guardan_cifrados(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _medicamento(cliente, titular, perfil_id)
    crudo = session.execute(
        text("SELECT nombre, dosis, frecuencia FROM medicamento WHERE id = :id"), {"id": med["id"]}
    ).one()
    for valor in crudo:
        assert valor.startswith("v1:k1:")
    assert "Losartán" not in crudo[0]


# ---------- registro de tomas ----------

def test_ultimo_registro_gana_y_no_se_borra_historia(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    toma_id = _tomas(cliente, titular, perfil_id, INICIO, INICIO).json()[0]["id"]

    primero = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "omitida"}, headers=cabecera(titular))
    assert primero.status_code == 201, primero.text
    segundo = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada"}, headers=cabecera(titular))
    assert segundo.status_code == 201

    toma = next(t for t in _tomas(cliente, titular, perfil_id, INICIO, INICIO).json() if t["id"] == toma_id)
    assert toma["estado"] == "tomada"
    assert toma["registro_id"] == segundo.json()["id"]

    registros = session.scalar(
        select(func.count()).select_from(TomaRegistro).where(TomaRegistro.toma_programada_id == uuid.UUID(toma_id))
    )
    assert registros == 2


def test_registro_con_mismo_identificador_es_idempotente(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    toma_id = _tomas(cliente, titular, perfil_id, INICIO, INICIO).json()[0]["id"]
    cliente_id = str(uuid.uuid4())

    a = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada", "id": cliente_id}, headers=cabecera(titular))
    b = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada", "id": cliente_id}, headers=cabecera(titular))
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["id"] == b.json()["id"] == cliente_id
    assert session.scalar(select(func.count()).select_from(TomaRegistro).where(TomaRegistro.id == uuid.UUID(cliente_id))) == 1


def test_identificador_de_registro_de_otra_toma_se_rechaza(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    tomas = _tomas(cliente, titular, perfil_id, INICIO, INICIO).json()
    cliente_id = str(uuid.uuid4())
    cliente.post(f"{BASE}/tomas/{tomas[0]['id']}/registros", json={"estado": "tomada", "id": cliente_id}, headers=cabecera(titular))
    r = cliente.post(f"{BASE}/tomas/{tomas[1]['id']}/registros", json={"estado": "tomada", "id": cliente_id}, headers=cabecera(titular))
    assert r.status_code == 422


def test_estado_de_toma_invalido_responde_422(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    toma_id = _tomas(cliente, titular, perfil_id, INICIO, INICIO).json()[0]["id"]
    r = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "quizas"}, headers=cabecera(titular))
    assert r.status_code == 422


def test_lector_puede_ver_pero_no_registrar_tomas(cliente, session):
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    _medicamento(cliente, titular, perfil_id)

    tomas = _tomas(cliente, lector, perfil_id, INICIO, INICIO)
    assert tomas.status_code == 200 and len(tomas.json()) == 2

    toma_id = tomas.json()[0]["id"]
    r = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada"}, headers=cabecera(lector))
    assert r.status_code == 403


def test_sin_acceso_no_se_revela_la_toma(cliente, session):
    titular = crear_usuario(session)
    extraño = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _medicamento(cliente, titular, perfil_id)
    toma_id = _tomas(cliente, titular, perfil_id, INICIO, INICIO).json()[0]["id"]

    assert _tomas(cliente, extraño, perfil_id, INICIO, INICIO).status_code == 404
    assert cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada"}, headers=cabecera(extraño)).status_code == 404
    assert cliente.post(f"{BASE}/tomas/{uuid.uuid4()}/registros", json={"estado": "tomada"}, headers=cabecera(extraño)).status_code == 404


def test_lector_no_puede_crear_medicamento(cliente, session):
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/medicamentos",
        json={
            "nombre": "X", "dosis": "1", "frecuencia": {"tipo": "horarios", "horas": ["08:00"]},
            "inicio": INICIO, "zona_horaria": BOGOTA,
        },
        headers=cabecera(lector),
    )
    assert r.status_code == 403


# ---------- síntomas ----------

def test_sintoma_se_registra_y_nota_va_cifrada(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/sintomas",
        json={"sintoma": "Dolor de cabeza", "intensidad": 6, "nota": "Tras la comida", "fecha": "2026-10-01T15:30:00-05:00"},
        headers=cabecera(titular),
    )
    assert r.status_code == 201, r.text
    crudo = session.execute(
        text("SELECT nota FROM sintoma_registro WHERE id = :id"), {"id": r.json()["id"]}
    ).scalar()
    assert crudo.startswith("v1:k1:")
    assert "Tras la comida" not in crudo

    listado = cliente.get(
        f"{BASE}/perfiles/{perfil_id}/sintomas",
        params={"desde": INICIO, "hasta": INICIO, "zona_horaria": BOGOTA},
        headers=cabecera(titular),
    )
    assert listado.status_code == 200
    assert listado.json()[0]["nota"] == "Tras la comida"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"sintoma": "Mareo", "intensidad": 11, "fecha": "2026-10-01T15:00:00-05:00"},
        {"sintoma": "Mareo", "intensidad": -1, "fecha": "2026-10-01T15:00:00-05:00"},
        {"sintoma": "Mareo", "intensidad": 3, "fecha": "2026-10-01T15:00:00"},
    ],
)
def test_sintoma_invalido_responde_422(cliente, session, cuerpo):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/sintomas", json=cuerpo, headers=cabecera(titular))
    assert r.status_code == 422


def test_sintoma_con_identificador_repetido_es_idempotente(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    sid = str(uuid.uuid4())
    cuerpo = {"id": sid, "sintoma": "Fiebre", "intensidad": 4, "fecha": "2026-10-01T10:00:00-05:00"}
    a = cliente.post(f"{BASE}/perfiles/{perfil_id}/sintomas", json=cuerpo, headers=cabecera(titular))
    b = cliente.post(f"{BASE}/perfiles/{perfil_id}/sintomas", json=cuerpo, headers=cabecera(titular))
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["id"] == b.json()["id"] == sid


# ---------- diagnósticos ----------

def test_diagnostico_resuelto_sale_del_listado_vigente(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    d = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/diagnosticos",
        json={"descripcion": "Esguince de tobillo", "fecha": "2026-09-20"},
        headers=cabecera(titular),
    )
    assert d.status_code == 201, d.text
    diagnostico_id = d.json()["id"]

    vigentes = cliente.get(
        f"{BASE}/perfiles/{perfil_id}/diagnosticos", params={"incluir_resueltos": False}, headers=cabecera(titular)
    )
    assert [x["id"] for x in vigentes.json()] == [diagnostico_id]

    r = cliente.patch(f"{BASE}/diagnosticos/{diagnostico_id}", json={"estado": "resuelto"}, headers=cabecera(titular))
    assert r.status_code == 200 and r.json()["estado"] == "resuelto"

    vigentes = cliente.get(
        f"{BASE}/perfiles/{perfil_id}/diagnosticos", params={"incluir_resueltos": False}, headers=cabecera(titular)
    )
    assert vigentes.json() == []


def test_diagnostico_con_zona_de_otro_perfil_se_rechaza(cliente, session):
    titular = crear_usuario(session)
    otro = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    perfil_otro = crear_perfil_de(cliente, otro, nombre="Otra persona")
    zona_ajena = ZonaConsulta(perfil_id=uuid.UUID(perfil_otro), nombre="Rodilla")
    session.add(zona_ajena)
    session.commit()

    r = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/diagnosticos",
        json={"descripcion": "Dolor", "fecha": "2026-09-20", "zona_id": str(zona_ajena.id)},
        headers=cabecera(titular),
    )
    assert r.status_code == 422


def test_diagnostico_descripcion_cifrada(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    d = cliente.post(
        f"{BASE}/perfiles/{perfil_id}/diagnosticos",
        json={"descripcion": "Hernia discal L4-L5", "fecha": "2026-09-20"},
        headers=cabecera(titular),
    )
    crudo = session.execute(text("SELECT descripcion FROM diagnostico WHERE id = :id"), {"id": d.json()["id"]}).scalar()
    assert crudo.startswith("v1:k1:")
    assert "Hernia" not in crudo


def test_diagnostico_sin_acceso_responde_404(cliente, session):
    titular = crear_usuario(session)
    extraño = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    r = cliente.get(f"{BASE}/perfiles/{perfil_id}/diagnosticos", headers=cabecera(extraño))
    assert r.status_code == 404
