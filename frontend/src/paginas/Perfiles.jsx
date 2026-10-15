import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ETIQUETAS_ALCANCE, ETIQUETAS_ROL, Mensaje, formatearFecha } from "../componentes.jsx";
import { AvisoConsentimiento } from "./MiCuenta.jsx";

export default function Perfiles() {
  const [perfiles, setPerfiles] = useState(null);
  const [error, setError] = useState("");
  const [creado, setCreado] = useState("");
  const [dependiente, setDependiente] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setPerfiles(await api("/api/v1/perfiles"));
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  async function crear(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    setError("");
    setCreado("");
    try {
      const perfil = await api("/api/v1/perfiles", {
        metodo: "POST",
        cuerpo: {
          nombre: datos.get("nombre"),
          fecha_nacimiento: datos.get("fecha_nacimiento"),
          dependiente,
        },
      });
      setCreado(`Perfil "${perfil.nombre}" creado`);
      formulario.reset();
      setDependiente(false);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="pagina">
      <h1>Mis perfiles</h1>
      <AvisoConsentimiento />
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{creado}</Mensaje>

      {perfiles === null && !error && <p className="cargando">Cargando perfiles…</p>}
      {perfiles && perfiles.length === 0 && <p>Aún no tienes perfiles. Crea el primero abajo.</p>}
      {perfiles && perfiles.length > 0 && (
        <ul className="lista">
          {perfiles.map((p) => (
            <li key={p.id}>
              <Link to={`/perfiles/${p.id}`} data-testid="enlace-perfil">{p.nombre}</Link>
              <span className="etiqueta">{ETIQUETAS_ROL[p.rol]} · {ETIQUETAS_ALCANCE[p.alcance]}</span>
              <span className="fecha">Nac. {formatearFecha(p.fecha_nacimiento)}</span>
            </li>
          ))}
        </ul>
      )}

      <section className="tarjeta">
        <h2>Crear perfil</h2>
        <form onSubmit={crear} className="formulario" data-testid="form-crear-perfil">
          <label>Nombre<input name="nombre" required maxLength={100} /></label>
          <label>Fecha de nacimiento<input name="fecha_nacimiento" type="date" required /></label>
          <label className="casilla">
            <input type="checkbox" checked={dependiente} onChange={(e) => setDependiente(e.target.checked)} />
            Es para un menor o un adulto a mi cargo (no tiene cuenta propia)
          </label>
          <button type="submit">Crear perfil</button>
        </form>
      </section>
    </div>
  );
}
