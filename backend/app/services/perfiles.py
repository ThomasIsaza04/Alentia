"""Reglas de perfiles, zonas de consulta y vínculos entre cuentas (paso 4, §9.6).

Toda función que recibe un perfil o una zona llama primero a `acceso_a`, que decide entre
404 (sin acceso vigente) y 403 (acceso insuficiente). Ningún endpoint lee datos de salud sin pasar por ahí.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errores import AccionInvalida, PermisoInsuficiente, RecursoNoEncontrado, ReglaNegocio
from app.core.tokens import hash_token, token_aleatorio
from app.db.base import ahora_utc
from app.models import AccesoPerfil, Auditoria, InvitacionPerfil, Perfil, Usuario, ZonaConsulta
from app.services.correo import MensajeCorreo, remitente

ORDEN_ALCANCE = {"lector": 1, "editor": 2, "admin": 3}
MAYORIA_DE_EDAD = 18
HORAS_INVITACION = 72


def es_menor(fecha_nacimiento: date, hoy: date) -> bool:
    """Menor de 18 años a la fecha indicada. El cumpleaños de hoy cuenta como cumplido."""
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad < MAYORIA_DE_EDAD


def _hoy() -> date:
    return ahora_utc().date()


def _vigente():
    """Un acceso cuenta si está activo y no tiene fecha de fin pasada o futura revocada."""
    return (AccesoPerfil.estado == "activo") & or_(
        AccesoPerfil.fin.is_(None), AccesoPerfil.fin > ahora_utc()
    )


def _auditar(db: Session, accion: str, actor: uuid.UUID, perfil_id: uuid.UUID | None) -> None:
    db.add(
        Auditoria(
            accion=accion,
            actor_usuario_id=actor,
            perfil_id=perfil_id,
            fecha=ahora_utc(),
        )
    )


def acceso_a(db: Session, usuario: Usuario, perfil_id: uuid.UUID, minimo: str) -> AccesoPerfil:
    acceso = db.scalar(
        select(AccesoPerfil).where(
            AccesoPerfil.usuario_id == usuario.id,
            AccesoPerfil.perfil_id == perfil_id,
            _vigente(),
        )
    )
    if acceso is None:
        raise RecursoNoEncontrado("Perfil no encontrado")
    if ORDEN_ALCANCE[acceso.alcance] < ORDEN_ALCANCE[minimo]:
        raise PermisoInsuficiente("Tu alcance en este perfil no permite esta acción")
    return acceso


def _tiene_representante(db: Session, perfil_id: uuid.UUID, excepto: uuid.UUID | None = None) -> bool:
    consulta = select(func.count()).select_from(AccesoPerfil).where(
        AccesoPerfil.perfil_id == perfil_id,
        AccesoPerfil.rol == "representante",
        _vigente(),
    )
    if excepto is not None:
        consulta = consulta.where(AccesoPerfil.id != excepto)
    return db.scalar(consulta) > 0


# ---------- perfiles ----------

def crear_perfil(
    db: Session, usuario: Usuario, nombre: str, fecha: date, dependiente: bool
) -> tuple[Perfil, AccesoPerfil]:
    hoy = _hoy()
    if fecha > hoy:
        raise ReglaNegocio("La fecha de nacimiento no puede ser futura")
    if es_menor(fecha, hoy) and not dependiente:
        raise ReglaNegocio(
            "Un menor de edad se registra como perfil dependiente, a cargo de un representante"
        )
    perfil = Perfil(
        nombre=nombre,
        fecha_nacimiento=fecha,
        titular_usuario_id=None if dependiente else usuario.id,
    )
    db.add(perfil)
    db.flush()
    acceso = AccesoPerfil(
        usuario_id=usuario.id,
        perfil_id=perfil.id,
        rol="representante" if dependiente else "titular",
        alcance="admin",
        estado="activo",
        inicio=ahora_utc(),
    )
    db.add(acceso)
    _auditar(db, "PERFIL_CREADO", usuario.id, perfil.id)
    db.commit()
    return perfil, acceso


def perfiles_de(db: Session, usuario: Usuario) -> list[tuple[Perfil, AccesoPerfil]]:
    filas = db.execute(
        select(Perfil, AccesoPerfil)
        .join(AccesoPerfil, AccesoPerfil.perfil_id == Perfil.id)
        .where(AccesoPerfil.usuario_id == usuario.id, _vigente())
        .order_by(Perfil.creado_en)
    ).all()
    return [(perfil, acceso) for perfil, acceso in filas]


def actualizar_perfil(
    db: Session,
    usuario: Usuario,
    perfil_id: uuid.UUID,
    nombre: str | None,
    fecha: date | None,
) -> tuple[Perfil, AccesoPerfil]:
    acceso = acceso_a(db, usuario, perfil_id, "editor")
    perfil = db.get(Perfil, perfil_id)
    if fecha is not None:
        hoy = _hoy()
        if fecha > hoy:
            raise ReglaNegocio("La fecha de nacimiento no puede ser futura")
        if es_menor(fecha, hoy) and not _tiene_representante(db, perfil_id):
            raise ReglaNegocio("Un perfil de menor debe tener al menos un representante")
        perfil.fecha_nacimiento = fecha
    if nombre is not None:
        perfil.nombre = nombre
    _auditar(db, "PERFIL_ACTUALIZADO", usuario.id, perfil_id)
    db.commit()
    return perfil, acceso


# ---------- zonas de consulta ----------

def crear_zona(db: Session, usuario: Usuario, perfil_id: uuid.UUID, nombre: str) -> ZonaConsulta:
    acceso_a(db, usuario, perfil_id, "editor")
    zona = ZonaConsulta(perfil_id=perfil_id, nombre=nombre, archivada=False)
    db.add(zona)
    db.flush()
    _auditar(db, "ZONA_CREADA", usuario.id, perfil_id)
    db.commit()
    return zona


def listar_zonas(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, incluir_archivadas: bool
) -> list[ZonaConsulta]:
    acceso_a(db, usuario, perfil_id, "lector")
    consulta = select(ZonaConsulta).where(ZonaConsulta.perfil_id == perfil_id)
    if not incluir_archivadas:
        consulta = consulta.where(ZonaConsulta.archivada.is_(False))
    return list(db.scalars(consulta.order_by(ZonaConsulta.nombre)))


def actualizar_zona(
    db: Session,
    usuario: Usuario,
    zona_id: uuid.UUID,
    nombre: str | None,
    archivada: bool | None,
) -> ZonaConsulta:
    zona = db.get(ZonaConsulta, zona_id)
    if zona is None:
        raise RecursoNoEncontrado("Zona no encontrada")
    acceso_a(db, usuario, zona.perfil_id, "editor")
    if nombre is not None:
        zona.nombre = nombre
    if archivada is not None:
        # Las zonas no se borran: los registros que dependen de ellas conservan su trazabilidad.
        zona.archivada = archivada
    _auditar(db, "ZONA_ACTUALIZADA", usuario.id, zona.perfil_id)
    db.commit()
    return zona


# ---------- accesos e invitaciones ----------

def listar_accesos(db: Session, usuario: Usuario, perfil_id: uuid.UUID) -> list[tuple[AccesoPerfil, str]]:
    acceso_a(db, usuario, perfil_id, "admin")
    filas = db.execute(
        select(AccesoPerfil, Usuario.correo)
        .join(Usuario, Usuario.id == AccesoPerfil.usuario_id)
        .where(AccesoPerfil.perfil_id == perfil_id, _vigente())
        .order_by(AccesoPerfil.inicio)
    ).all()
    return [(acceso, correo) for acceso, correo in filas]


def invitar(
    db: Session, usuario: Usuario, perfil_id: uuid.UUID, correo: str, alcance: str
) -> None:
    acceso_a(db, usuario, perfil_id, "admin")
    correo_normalizado = correo.strip().lower()
    if correo_normalizado == usuario.correo:
        raise ReglaNegocio("No puedes invitarte a ti mismo")
    token = token_aleatorio()
    db.add(
        InvitacionPerfil(
            perfil_id=perfil_id,
            correo_invitado=correo_normalizado,
            alcance=alcance,
            hash_token=hash_token(token),
            creada_por=usuario.id,
            vence_en=ahora_utc() + timedelta(hours=HORAS_INVITACION),
        )
    )
    _auditar(db, "INVITACION_CREADA", usuario.id, perfil_id)
    db.commit()
    remitente.enviar(
        MensajeCorreo(
            correo_normalizado,
            "Te invitaron a un perfil en Alentia",
            "Enlace para aceptar (válido 72 horas): "
            f"{settings.frontend_url}/aceptar-invitacion?token={token}",
        )
    )


def aceptar_invitacion(db: Session, usuario: Usuario, token: str) -> uuid.UUID:
    invitacion = db.scalar(
        select(InvitacionPerfil).where(
            InvitacionPerfil.hash_token == hash_token(token),
            InvitacionPerfil.aceptada_en.is_(None),
            InvitacionPerfil.vence_en > ahora_utc(),
        )
    )
    # Mismo mensaje para token inexistente, usado, vencido o dirigido a otra cuenta.
    if invitacion is None or invitacion.correo_invitado != usuario.correo:
        raise AccionInvalida("La invitación no es válida o ya venció")

    existente = db.scalar(
        select(AccesoPerfil).where(
            AccesoPerfil.usuario_id == usuario.id,
            AccesoPerfil.perfil_id == invitacion.perfil_id,
        )
    )
    if existente is not None and existente.estado == "activo" and (
        existente.fin is None or existente.fin > ahora_utc()
    ):
        raise ReglaNegocio("Ya tienes acceso a este perfil")

    ahora = ahora_utc()
    if existente is None:
        existente = AccesoPerfil(usuario_id=usuario.id, perfil_id=invitacion.perfil_id)
        db.add(existente)
    # Un acceso revocado se reactiva; nunca se crea un duplicado (UNIQUE usuario_id, perfil_id).
    existente.rol = "cuidador"
    existente.alcance = invitacion.alcance
    existente.estado = "activo"
    existente.inicio = ahora
    existente.fin = None
    invitacion.aceptada_en = ahora
    _auditar(db, "INVITACION_ACEPTADA", usuario.id, invitacion.perfil_id)
    db.commit()
    return invitacion.perfil_id


def revocar_acceso(db: Session, usuario: Usuario, perfil_id: uuid.UUID, acceso_id: uuid.UUID) -> None:
    acceso_a(db, usuario, perfil_id, "admin")
    objetivo = db.get(AccesoPerfil, acceso_id)
    if objetivo is None or objetivo.perfil_id != perfil_id or objetivo.estado != "activo":
        raise RecursoNoEncontrado("Acceso no encontrado")
    if objetivo.rol == "titular":
        raise ReglaNegocio("El titular no puede retirar su propio acceso")
    perfil = db.get(Perfil, perfil_id)
    if (
        objetivo.rol == "representante"
        and es_menor(perfil.fecha_nacimiento, _hoy())
        and not _tiene_representante(db, perfil_id, excepto=objetivo.id)
    ):
        raise ReglaNegocio("Un perfil de menor debe conservar al menos un representante")
    objetivo.estado = "revocado"
    objetivo.fin = ahora_utc()
    _auditar(db, "ACCESO_REVOCADO", usuario.id, perfil_id)
    db.commit()
