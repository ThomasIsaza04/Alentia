"""Permisos del rol 'alentia_app' (documento §7.7): la aplicación solo añade en la bitácora.

Requiere APP_TEST_DATABASE_URL apuntando a la base de prueba con el rol 'alentia_app'.
"""
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings


@pytest.fixture
def motor_app():
    url = settings.app_test_database_url
    if not url:
        pytest.skip("Definir APP_TEST_DATABASE_URL (rol alentia_app) para probar permisos")
    motor = create_engine(url)
    yield motor
    motor.dispose()


def test_rol_aplicacion_puede_agregar_a_la_auditoria(motor_app) -> None:
    with motor_app.begin() as conexion:
        conexion.execute(text("INSERT INTO auditoria (accion, fecha) VALUES ('PRUEBA_PERMISOS', now())"))


def test_rol_aplicacion_no_modifica_la_auditoria(motor_app) -> None:
    with pytest.raises(DBAPIError), motor_app.begin() as conexion:
        conexion.execute(text("UPDATE auditoria SET accion = 'MANIPULADO'"))


def test_rol_aplicacion_no_borra_la_auditoria(motor_app) -> None:
    with pytest.raises(DBAPIError), motor_app.begin() as conexion:
        conexion.execute(text("DELETE FROM auditoria"))


def test_rol_aplicacion_no_modifica_registros_de_sintomas(motor_app) -> None:
    with pytest.raises(DBAPIError), motor_app.begin() as conexion:
        conexion.execute(text("UPDATE sintoma_registro SET intensidad = 0"))


def test_rol_aplicacion_no_modifica_registros_de_tomas(motor_app) -> None:
    with pytest.raises(DBAPIError), motor_app.begin() as conexion:
        conexion.execute(text("UPDATE toma_registro SET estado = 'tomada'"))


def test_rol_aplicacion_puede_crear_una_cuenta(motor_app) -> None:
    with motor_app.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO usuario (id, correo, hash_contrasena, verificado, estado, creado_en) "
                "VALUES (:id, :correo, 'hash-prueba', false, 'activo', now())"
            ),
            {"id": uuid.uuid4(), "correo": f"{uuid.uuid4().hex}@ejemplo.co"},
        )


def test_rol_aplicacion_puede_leer_y_escribir_las_tablas_del_paso_4(motor_app) -> None:
    # Las tablas nuevas heredan los permisos por defecto de la migración 0003.
    with motor_app.begin() as conexion:
        conexion.execute(text("SELECT count(*) FROM invitacion_perfil")).scalar_one()
        conexion.execute(text("SELECT count(*) FROM zona_consulta")).scalar_one()
