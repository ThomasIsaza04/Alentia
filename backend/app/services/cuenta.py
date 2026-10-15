"""Exportación, eliminación con período de gracia y purga de cuentas (RF-CON-03 y RF-CON-04)."""
import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core import passwords
from app.core.errores import PermisoInsuficiente
from app.db.base import ahora_utc
from app.models import (
    AccesoPerfil,
    AccesoTemporal,
    Auditoria,
    Diagnostico,
    Medicamento,
    Perfil,
    SintomaRegistro,
    TomaProgramada,
    TomaRegistro,
    Usuario,
    ZonaConsulta,
)
from app.services import acceso_temporal as acceso_svc
from app.services import consentimiento as consentimientos
from app.services.perfiles import _vigente

DIAS_DE_GRACIA = 7


# ---------- exportación ----------

def _perfiles_del_titular(db: Session, usuario: Usuario) -> list[Perfil]:
    """Perfiles de los que el usuario es titular o representante con acceso vigente."""
    return list(
        db.scalars(
            select(Perfil)
            .join(AccesoPerfil, AccesoPerfil.perfil_id == Perfil.id)
            .where(
                AccesoPerfil.usuario_id == usuario.id,
                AccesoPerfil.rol.in_(("titular", "representante")),
                _vigente(),
            )
            .order_by(Perfil.creado_en)
        ).unique()
    )


def _perfil_a_dict(db: Session, perfil: Perfil) -> dict:
    zonas = list(db.scalars(select(ZonaConsulta).where(ZonaConsulta.perfil_id == perfil.id)))
    nombres_zona = {z.id: z.nombre for z in zonas}

    medicamentos = []
    for m in db.scalars(select(Medicamento).where(Medicamento.perfil_id == perfil.id).order_by(Medicamento.inicio)):
        tomas = []
        for t in db.scalars(
            select(TomaProgramada).where(TomaProgramada.medicamento_id == m.id).order_by(TomaProgramada.programada_en)
        ):
            registros = list(
                db.scalars(
                    select(TomaRegistro)
                    .where(TomaRegistro.toma_programada_id == t.id)
                    .order_by(TomaRegistro.registrada_en)
                )
            )
            tomas.append(
                {
                    "programada_en": t.programada_en.isoformat(),
                    "registros": [{"estado": r.estado, "registrada_en": r.registrada_en.isoformat()} for r in registros],
                }
            )
        medicamentos.append(
            {
                "nombre": m.nombre,
                "dosis": m.dosis,
                "frecuencia": m.frecuencia,
                "inicio": m.inicio.isoformat(),
                "fin": m.fin.isoformat() if m.fin else None,
                "activo": m.activo,
                "tomas": tomas,
            }
        )

    sintomas = [
        {"sintoma": s.sintoma, "intensidad": s.intensidad, "nota": s.nota, "fecha": s.fecha.isoformat()}
        for s in db.scalars(select(SintomaRegistro).where(SintomaRegistro.perfil_id == perfil.id).order_by(SintomaRegistro.fecha))
    ]
    diagnosticos = [
        {
            "descripcion": d.descripcion,
            "fecha": d.fecha.isoformat(),
            "estado": d.estado,
            "zona": nombres_zona.get(d.zona_id) if d.zona_id else None,
        }
        for d in db.scalars(select(Diagnostico).where(Diagnostico.perfil_id == perfil.id).order_by(Diagnostico.fecha))
    ]
    accesos = []
    ahora = ahora_utc()
    for a in db.scalars(select(AccesoTemporal).where(AccesoTemporal.perfil_id == perfil.id).order_by(AccesoTemporal.creado_en)):
        accesos.append(
            {
                "categorias": a.categorias.split(","),
                "duracion_minutos": a.duracion_minutos,
                "creado_en": a.creado_en.isoformat(),
                "vence_en": a.vence_en.isoformat(),
                "estado": acceso_svc.estado_de(a, ahora),
                # Nunca se exportan tokens ni hashes.
            }
        )
    return {
        "nombre": perfil.nombre,
        "fecha_nacimiento": perfil.fecha_nacimiento.isoformat(),
        "zonas": [{"nombre": z.nombre, "archivada": z.archivada} for z in zonas],
        "medicamentos": medicamentos,
        "sintomas": sintomas,
        "diagnosticos": diagnosticos,
        "accesos_temporales": accesos,
    }


def datos_exportacion(db: Session, usuario: Usuario) -> dict:
    ahora = ahora_utc()
    historial = consentimientos.historial(db, usuario)
    db.add(Auditoria(accion="EXPORTACION_SOLICITADA", actor_usuario_id=usuario.id, perfil_id=None, fecha=ahora))
    db.commit()
    return {
        "generado_en": ahora.isoformat(),
        "cuenta": {
            "correo": usuario.correo,
            "creada_en": usuario.creado_en.isoformat(),
            "consentimientos": [
                {
                    "finalidad": c.finalidad,
                    "version": c.version,
                    "aceptado": c.aceptado,
                    "ocurrido_en": c.ocurrido_en.isoformat(),
                }
                for c in historial
            ],
        },
        "perfiles": [_perfil_a_dict(db, p) for p in _perfiles_del_titular(db, usuario)],
    }


def exportacion_csv(datos: dict) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["seccion", "perfil", "fecha", "detalle", "estado"])
    for c in datos["cuenta"]["consentimientos"]:
        escritor.writerow(["consentimiento", "", c["ocurrido_en"], f"{c['finalidad']} v{c['version']}", "aceptado" if c["aceptado"] else "retirado"])
    for p in datos["perfiles"]:
        nombre = p["nombre"]
        for m in p["medicamentos"]:
            escritor.writerow(["medicamento", nombre, m["inicio"], f"{m['nombre']} {m['dosis']}", "activo" if m["activo"] else "inactivo"])
            for t in m["tomas"]:
                ultimo = t["registros"][-1]["estado"] if t["registros"] else "pendiente"
                escritor.writerow(["toma", nombre, t["programada_en"], f"{m['nombre']}", ultimo])
        for s in p["sintomas"]:
            escritor.writerow(["sintoma", nombre, s["fecha"], f"{s['sintoma']} intensidad {s['intensidad']}" + (f" · {s['nota']}" if s["nota"] else ""), ""])
        for d in p["diagnosticos"]:
            escritor.writerow(["diagnostico", nombre, d["fecha"], d["descripcion"], d["estado"]])
        for a in p["accesos_temporales"]:
            escritor.writerow(["acceso_temporal", nombre, a["creado_en"], ",".join(a["categorias"]), a["estado"]])
    return salida.getvalue()


# ---------- eliminación ----------

def solicitar_eliminacion(db: Session, usuario: Usuario, clave: str) -> datetime:
    if not passwords.verificar(clave, usuario.hash_contrasena):
        raise PermisoInsuficiente("La contraseña no es correcta")
    if usuario.eliminar_en is None:
        usuario.eliminar_en = ahora_utc() + timedelta(days=DIAS_DE_GRACIA)
        db.add(Auditoria(accion="ELIMINACION_SOLICITADA", actor_usuario_id=usuario.id, perfil_id=None, fecha=ahora_utc()))
        db.commit()
    return usuario.eliminar_en


def cancelar_eliminacion(db: Session, usuario: Usuario) -> None:
    if usuario.eliminar_en is not None:
        usuario.eliminar_en = None
        db.add(Auditoria(accion="ELIMINACION_CANCELADA", actor_usuario_id=usuario.id, perfil_id=None, fecha=ahora_utc()))
        db.commit()


def eliminar_vencidas(db: Session, ahora: datetime) -> int:
    """Borra definitivamente las cuentas cuyo período de gracia venció.

    Cada cuenta va en su propia transacción. Los perfiles de los que el titular es dueño se borran
    con todos sus registros; los accesos de otras personas a esos perfiles desaparecen en cascada.
    La auditoría queda sin identificador de usuario ni de perfil.
    """
    pendientes = list(db.scalars(select(Usuario.id).where(Usuario.eliminar_en.is_not(None), Usuario.eliminar_en <= ahora)))
    eliminadas = 0
    for usuario_id in pendientes:
        # Permiso de borrado solo dentro de esta transacción (ver app/db/triggers.py).
        db.execute(text("SELECT set_config('alentia.permitir_borrado', 'on', true)"))
        db.execute(delete(Perfil).where(Perfil.titular_usuario_id == usuario_id))
        db.execute(delete(Usuario).where(Usuario.id == usuario_id))
        db.add(Auditoria(accion="CUENTA_ELIMINADA", actor_usuario_id=None, perfil_id=None, fecha=ahora_utc()))
        db.commit()
        eliminadas += 1
    return eliminadas
