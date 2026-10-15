import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { ETIQUETAS_ALCANCE, ETIQUETAS_ROL, Mensaje, formatearFecha } from "../componentes.jsx";

export default function PerfilDetalle() {
  const { id } = useParams();
  const [perfil, setPerfil] = useState(null);
  const [zonas, setZonas] = useState([]);
  const [accesos, setAccesos] = useState([]);
  const [mostrarArchivadas, setMostrarArchivadas] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const cargar = useCallback(async () => {
    try {
      const p = await api(`/api/v1/perfiles/${id}`);
      setPerfil(p);
      setZonas(await api(`/api/v1/perfiles/${id}/zonas?incluir_archivadas=${mostrarArchivadas}`));
      if (p.alcance === "admin") {
        setAccesos(await api(`/api/v1/perfiles/${id}/accesos`));
      } else {
        setAccesos([]);
      }
    } catch (e) {
      setError(e.message);
    }
  }, [id, mostrarArchivadas]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const puedeEditar = perfil && (perfil.alcance === "editor" || perfil.alcance === "admin");
  const esAdmin = perfil && perfil.alcance === "admin";

  async function ejecutar(accion, mensajeOk) {
    setError("");
    setAviso("");
    try {
      await accion();
      // Una acción puede fijar su propio aviso (p. ej. la invitación); en ese caso no se sobrescribe.
      if (mensajeOk) setAviso(mensajeOk);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function agregarZona(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const nombre = new FormData(formulario).get("nombre");
    await ejecutar(async () => {
      await api(`/api/v1/perfiles/${id}/zonas`, { metodo: "POST", cuerpo: { nombre } });
      formulario.reset();
    }, "Zona creada");
  }

  async function editarPerfil(evento) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    const cuerpo = { nombre: datos.get("nombre") };
    if (datos.get("fecha_nacimiento")) cuerpo.fecha_nacimiento = datos.get("fecha_nacimiento");
    await ejecutar(() => api(`/api/v1/perfiles/${id}`, { metodo: "PATCH", cuerpo }), "Perfil actualizado");
  }

  async function invitar(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    await ejecutar(async () => {
      const r = await api(`/api/v1/perfiles/${id}/invitaciones`, {
        metodo: "POST",
        cuerpo: { correo: datos.get("correo"), alcance: datos.get("alcance") },
      });
      setAviso(r.mensaje);
      formulario.reset();
    }, "");
  }

  if (error && !perfil) {
    return (
      <div className="pagina">
        <Mensaje>{error}</Mensaje>
        <Link to="/">Volver a mis perfiles</Link>
      </div>
    );
  }
  if (!perfil) return <p className="cargando">Cargando…</p>;

  return (
    <div className="pagina">
      <p><Link to="/">← Mis perfiles</Link></p>
      <h1 data-testid="titulo-perfil">{perfil.nombre}</h1>
      <p>
        Nacimiento: {formatearFecha(perfil.fecha_nacimiento)} · {ETIQUETAS_ROL[perfil.rol]} ·{" "}
        {ETIQUETAS_ALCANCE[perfil.alcance]}
      </p>
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      <section className="tarjeta">
        <h2>Salud</h2>
        <ul className="lista">
          <li><Link to={`/perfiles/${id}/medicacion`} data-testid="enlace-medicacion">Medicación y tomas de hoy</Link></li>
          <li><Link to={`/perfiles/${id}/sintomas`} data-testid="enlace-sintomas">Síntomas</Link></li>
          <li><Link to={`/perfiles/${id}/diagnosticos`} data-testid="enlace-diagnosticos">Diagnósticos</Link></li>
          <li><Link to={`/perfiles/${id}/acceso`} data-testid="enlace-acceso">Acceso para profesional (QR y PIN)</Link></li>
        </ul>
      </section>

      {puedeEditar && (
        <section className="tarjeta">
          <h2>Editar perfil</h2>
          <form onSubmit={editarPerfil} className="formulario" data-testid="form-editar-perfil">
            <label>Nombre<input name="nombre" defaultValue={perfil.nombre} required maxLength={100} /></label>
            <label>Fecha de nacimiento (opcional)<input name="fecha_nacimiento" type="date" /></label>
            <button type="submit">Guardar cambios</button>
          </form>
        </section>
      )}

      <section className="tarjeta">
        <h2>Zonas de consulta</h2>
        <label className="casilla">
          <input type="checkbox" checked={mostrarArchivadas} onChange={(e) => setMostrarArchivadas(e.target.checked)} />
          Mostrar archivadas
        </label>
        {zonas.length === 0 && <p>No hay zonas todavía.</p>}
        <ul className="lista" data-testid="lista-zonas">
          {zonas.map((z) => (
            <li key={z.id}>
              <span className={z.archivada ? "archivada" : ""}>{z.nombre}</span>
              {z.archivada && <span className="etiqueta">archivada</span>}
              {puedeEditar && (
                <button
                  className="secundario"
                  onClick={() =>
                    ejecutar(
                      () => api(`/api/v1/zonas/${z.id}`, { metodo: "PATCH", cuerpo: { archivada: !z.archivada } }),
                      z.archivada ? "Zona restaurada" : "Zona archivada"
                    )
                  }
                >
                  {z.archivada ? "Restaurar" : "Archivar"}
                </button>
              )}
            </li>
          ))}
        </ul>
        {puedeEditar && (
          <form onSubmit={agregarZona} className="formulario en-linea" data-testid="form-zona">
            <label>Nueva zona<input name="nombre" required maxLength={100} placeholder="Ej.: Cardiología" /></label>
            <button type="submit">Agregar</button>
          </form>
        )}
      </section>

      {esAdmin && (
        <section className="tarjeta">
          <h2>Personas con acceso</h2>
          <ul className="lista" data-testid="lista-accesos">
            {accesos.map((a) => (
              <li key={a.id}>
                <span>{a.correo}</span>
                <span className="etiqueta">{ETIQUETAS_ROL[a.rol]} · {ETIQUETAS_ALCANCE[a.alcance]}</span>
                {a.rol !== "titular" && (
                  <button
                    className="secundario peligro"
                    onClick={() =>
                      ejecutar(() => api(`/api/v1/perfiles/${id}/accesos/${a.id}`, { metodo: "DELETE" }), "Acceso revocado")
                    }
                  >
                    Revocar
                  </button>
                )}
              </li>
            ))}
          </ul>

          <h3>Invitar a alguien</h3>
          <form onSubmit={invitar} className="formulario en-linea" data-testid="form-invitar">
            <label>Correo<input name="correo" type="email" required /></label>
            <label>
              Alcance
              <select name="alcance" defaultValue="lector">
                <option value="lector">Lector (solo consulta)</option>
                <option value="editor">Editor (puede editar)</option>
                <option value="admin">Administrador (puede invitar)</option>
              </select>
            </label>
            <button type="submit">Enviar invitación</button>
          </form>
          <p className="ayuda">La invitación vence en 72 horas. En desarrollo, el enlace aparece en la consola del backend.</p>
        </section>
      )}
    </div>
  );
}
