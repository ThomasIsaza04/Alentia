"""Pruebas de tomas atrasadas y omitidas, extensión, recordatorios y calendario (paso 9) contra PostgreSQL."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import get_db
from app.main import app
from app.models import Medicamento, TomaProgramada, TomaRegistro
from app.services import calendario
from app.services.tareas import estado_atraso, extender_tomas, marcar_omitidas
from tests.test_perfiles_api import BASE, cabecera, crear_perfil_de, crear_usuario, dar_acceso

BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def cliente(session):
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


def _pauta(cliente, titular, perfil_id, horas, inicio=None, nombre="Losartán", fin=None):
    cuerpo = {
        "nombre": nombre, "dosis": "50 mg", "frecuencia": {"tipo": "horarios", "horas": horas},
        "inicio": inicio or datetime.now(BOGOTA).date().isoformat(), "zona_horaria": "America/Bogota",
    }
    if fin:
        cuerpo["fin"] = fin
    r = cliente.post(f"{BASE}/perfiles/{perfil_id}/medicamentos", json=cuerpo, headers=cabecera(titular))
    assert r.status_code == 201, r.text
    return r.json()


def _hora_hace(horas: int) -> str:
    return (datetime.now(BOGOTA) - timedelta(hours=horas)).strftime("%H:%M")


# ---------- estados ----------

def test_estado_atrasada_tras_la_ventana_y_no_antes():
    ahora = datetime.now(timezone.utc)
    assert estado_atraso(ahora - timedelta(minutes=30), None, ahora) is None
    assert estado_atraso(ahora - timedelta(hours=3), None, ahora) == "atrasada"
    assert estado_atraso(ahora - timedelta(hours=3), "tomada", ahora) == "tomada"


def test_lista_de_tomas_muestra_atrasada(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    hora = _hora_hace(4)
    if int(hora[:2]) > int(datetime.now(BOGOTA).strftime("%H")):
        pytest.skip("La hora calculada cruza la medianoche; la prueba se repite otro momento del día")
    _pauta(cliente, titular, perfil_id, [hora])
    hoy = datetime.now(BOGOTA).date().isoformat()
    tomas = cliente.get(f"{BASE}/perfiles/{perfil_id}/tomas", params={"desde": hoy, "hasta": hoy, "zona_horaria": "America/Bogota"},
                        headers=cabecera(titular)).json()
    assert any(t["hora_local"] == hora and t["estado"] == "atrasada" for t in tomas)


def test_omitir_automaticamente_persiste_registro_del_sistema(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _pauta(cliente, titular, perfil_id, ["08:00"], inicio="2026-10-01")
    antes = session.scalar(select(func.count()).select_from(TomaRegistro))
    marcadas = marcar_omitidas(session, datetime(2026, 10, 1, 13, 0, tzinfo=timezone.utc) + timedelta(hours=13))
    assert marcadas >= 1
    registro = session.scalars(select(TomaRegistro).order_by(TomaRegistro.registrada_en.desc())).first()
    assert registro.estado == "omitida" and registro.registrada_por is None
    assert session.scalar(select(func.count()).select_from(TomaRegistro)) == antes + marcadas
    # Repetir la tarea no vuelve a omitir las mismas tomas.
    assert marcar_omitidas(session, datetime(2026, 10, 1, 13, 0, tzinfo=timezone.utc) + timedelta(hours=13)) == 0


def test_omitidas_por_sistema_no_bloquean_una_toma_confirmada_despues(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _pauta(cliente, titular, perfil_id, ["08:00"], inicio="2026-10-01")
    marcar_omitidas(session, datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc))
    toma_id = session.scalar(
        select(TomaProgramada.id)
        .where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))
        .order_by(TomaProgramada.programada_en)
        .limit(1)
    )
    r = cliente.post(f"{BASE}/tomas/{toma_id}/registros", json={"estado": "tomada"}, headers=cabecera(titular))
    assert r.status_code == 201
    tomas = cliente.get(f"{BASE}/perfiles/{perfil_id}/tomas", params={"desde": "2026-10-01", "hasta": "2026-10-01", "zona_horaria": "America/Bogota"},
                        headers=cabecera(titular)).json()
    assert tomas[0]["estado"] == "tomada"


# ---------- extensión ----------

def test_extension_programa_mas_dias_sin_duplicar(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _pauta(cliente, titular, perfil_id, ["08:00"])
    antes = session.scalar(select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"])))
    ahora_futuro = datetime.now(timezone.utc) + timedelta(days=16)
    extender_tomas(session, ahora_futuro)
    despues = session.scalar(select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"])))
    # Pauta de 1 toma diaria: los días 31 a 45 desde hoy, es decir 16 tomas nuevas.
    assert despues - antes == 16
    # Segunda ejecución: esta pauta ya está cubierta y no se duplica.
    extender_tomas(session, ahora_futuro)
    assert session.scalar(select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"]))) == despues


def test_extension_respeta_el_fin_de_la_pauta(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    hoy = datetime.now(BOGOTA).date()
    med = _pauta(cliente, titular, perfil_id, ["08:00"], inicio=hoy.isoformat(), fin=(hoy + timedelta(days=20)).isoformat())
    total_antes = session.scalar(select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"])))
    extender_tomas(session, datetime.now(timezone.utc) + timedelta(days=16))
    total = session.scalar(select(func.count()).select_from(TomaProgramada).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"])))
    ultima = session.scalar(select(func.max(TomaProgramada.programada_en)).where(TomaProgramada.medicamento_id == uuid.UUID(med["id"])))
    assert total == total_antes  # ya cubre hasta el fin (21 días) y no hay más que programar
    assert ultima.astimezone(BOGOTA).date() <= hoy + timedelta(days=20)


def test_pauta_desactivada_no_se_extiende(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _pauta(cliente, titular, perfil_id, ["08:00"])
    cliente.patch(f"{BASE}/medicamentos/{med['id']}", json={"activo": False}, headers=cabecera(titular))
    assert extender_tomas(session, datetime.now(timezone.utc) + timedelta(days=16)) == 0


def test_la_zona_de_la_pauta_queda_guardada(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    med = _pauta(cliente, titular, perfil_id, ["08:00"])
    fila = session.get(Medicamento, uuid.UUID(med["id"]))
    assert fila.zona_horaria == "America/Bogota"


# ---------- recordatorios ----------

def test_recordatorios_listan_tomas_vencidas_con_aviso(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _pauta(cliente, titular, perfil_id, [_hora_hace(4)] if int(_hora_hace(4)[:2]) <= int(datetime.now(BOGOTA).strftime("%H")) else ["00:01"])
    r = cliente.get(f"{BASE}/recordatorios", params={"zona_horaria": "America/Bogota"}, headers=cabecera(titular))
    assert r.status_code == 200
    cuerpo = r.json()
    assert "no reemplaza la indicación médica" in cuerpo["aviso"]
    assert all({"nombre", "hora_local", "estado", "toma_id"} <= set(i) for i in cuerpo["items"])


def test_recordatorios_exigen_consentimiento_de_notificaciones(cliente, session):
    titular = crear_usuario(session)
    cliente.post(f"{BASE}/cuenta/consentimientos",
                 json={"finalidad": "notificaciones", "version": "2026-10-v1", "aceptado": False}, headers=cabecera(titular))
    r = cliente.get(f"{BASE}/recordatorios", headers=cabecera(titular))
    assert r.status_code == 403


def test_recordatorios_de_un_lector_no_aparecen(cliente, session):
    titular = crear_usuario(session)
    lector = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    dar_acceso(session, lector, perfil_id, rol="cuidador", alcance="lector")
    _pauta(cliente, titular, perfil_id, ["00:01"])
    r = cliente.get(f"{BASE}/recordatorios", headers=cabecera(lector))
    assert r.json()["items"] == []


# ---------- calendario .ics ----------

def test_ics_tiene_un_evento_por_toma_con_alarma_y_aviso(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    _pauta(cliente, titular, perfil_id, ["08:00", "20:00"], inicio=datetime.now(BOGOTA).date().isoformat())
    r = cliente.get(f"{BASE}/perfiles/{perfil_id}/calendario.ics", headers=cabecera(titular))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["Content-Disposition"]
    texto = r.text.replace("\r\n ", "")
    assert texto.startswith("BEGIN:VCALENDAR\r\n") and texto.rstrip().endswith("END:VCALENDAR")
    assert texto.count("BEGIN:VEVENT") == texto.count("END:VEVENT") >= 2
    assert texto.count("BEGIN:VALARM") == texto.count("BEGIN:VEVENT")
    assert "no reemplaza la indicación médica" in texto
    assert re.search(r"DTSTART:\d{8}T\d{6}Z", texto)


def test_ics_escapa_comas_y_pliega_lineas_largas(cliente, session):
    titular = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    nombre = "Losartán, potásico " + "x" * 120
    _pauta(cliente, titular, perfil_id, ["08:00"], nombre=nombre[:100])
    texto = cliente.get(f"{BASE}/perfiles/{perfil_id}/calendario.ics", headers=cabecera(titular)).text
    assert "Losartán\\, potásico" in texto
    assert all(len(linea.encode("utf-8")) <= 75 for linea in texto.split("\r\n"))


def test_ics_sin_acceso_responde_404(cliente, session):
    titular = crear_usuario(session)
    extraño = crear_usuario(session)
    perfil_id = crear_perfil_de(cliente, titular)
    assert cliente.get(f"{BASE}/perfiles/{perfil_id}/calendario.ics", headers=cabecera(extraño)).status_code == 404


def test_escapado_de_texto_rfc5545():
    assert calendario._escapar("a,b;c\\d") == "a\\,b\;c\\\\d"
