import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { Mensaje, formatearFecha } from "../componentes.jsx";

// Vista del profesional: sin cuenta, solo lectura. La sesión vive en memoria y nunca se guarda.
// La página no carga scripts ni recursos de terceros y no envía la dirección como referencia.

export default function AccesoProfesional() {
  const { token } = useParams();
  const [fase, setFase] = useState("cargando"); // cargando | pin | resumen | terminado
  const [mensaje, setMensaje] = useState("");
  const [sesion, setSesion] = useState(null);
  const [resumen, setResumen] = useState(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.appendChild(meta);
    return () => meta.remove();
  }, []);

  useEffect(() => {
    api("/api/v1/acceso-profesional/abrir", { metodo: "POST", cuerpo: { token }, sinSesion: true })
      .then(() => setFase("pin"))
      .catch((e) => {
        setMensaje(e.message);
        setFase("terminado");
      });
  }, [token]);

  async function cargarResumen(tokenSesion) {
    const r = await fetch("/api/v1/acceso-profesional/resumen", {
      headers: { Authorization: `Bearer ${tokenSesion}` },
      cache: "no-store",
      referrerPolicy: "no-referrer",
    });
    if (!r.ok) {
      const datos = await r.json().catch(() => ({}));
      throw new Error(datos.detail || "No se pudo cargar el resumen");
    }
    return r.json();
  }

  async function verificar(evento) {
    evento.preventDefault();
    const pin = new FormData(evento.currentTarget).get("pin");
    setMensaje("");
    setOcupado(true);
    try {
      const datos = await api("/api/v1/acceso-profesional/verificar", {
        metodo: "POST",
        cuerpo: { token, pin },
        sinSesion: true,
      });
      setSesion(datos.sesion_token);
      setResumen(await cargarResumen(datos.sesion_token));
      setFase("resumen");
    } catch (e) {
      setMensaje(e.message);
      // Un error de acceso (usado, bloqueado, vencido) cierra la pantalla de PIN.
      if (e.status === 404) setFase("terminado");
    } finally {
      setOcupado(false);
    }
  }

  async function actualizar() {
    setMensaje("");
    try {
      setResumen(await cargarResumen(sesion));
    } catch (e) {
      setMensaje(e.message);
      setSesion(null);
      setResumen(null);
      setFase("terminado");
    }
  }

  return (
    <div className="pagina">
      <h1>Acceso de consulta</h1>
      <Mensaje>{mensaje}</Mensaje>

      {fase === "cargando" && <p className="cargando">Comprobando el enlace…</p>}

      {fase === "pin" && (
        <section className="tarjeta">
          <p>Escribe el PIN de 6 dígitos que te dio el paciente. Tienes 5 intentos.</p>
          <form onSubmit={verificar} className="formulario" data-testid="form-pin">
            <label>PIN<input name="pin" inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="one-time-code" required /></label>
            <button type="submit" disabled={ocupado}>Ver registros</button>
          </form>
        </section>
      )}

      {fase === "terminado" && (
        <section className="tarjeta">
          <p>Este enlace ya no está disponible. Pide al paciente un código nuevo.</p>
        </section>
      )}

      {fase === "resumen" && resumen && (
        <>
          <section className="tarjeta" data-testid="resumen-profesional">
            <h2 data-testid="resumen-perfil">{resumen.perfil_nombre}</h2>
            <p className="aviso-origen" data-testid="aviso-origen">{resumen.aviso}</p>
            <p className="ayuda">Generado {formatearFecha(resumen.generado_en)} · solo lectura</p>
          </section>
          {resumen.secciones.map((s) => (
            <section className="tarjeta" key={s.clave} data-testid={`seccion-${s.clave}`}>
              <h2>{s.titulo}</h2>
              {s.sin_informacion && <p data-testid="sin-informacion">Sin información registrada</p>}
              <ul className="lista">
                {s.lineas.map((l, i) => (
                  <li key={i} className={l.destacado ? "destacado" : ""} data-testid="linea-resumen">
                    <span>{l.texto}</span>
                    <span className="fecha">{formatearFecha(l.fecha)}</span>
                    {l.destacado && <span className="etiqueta">Se repite 3 o más días seguidos</span>}
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <button className="secundario" onClick={actualizar}>Actualizar</button>
        </>
      )}
    </div>
  );
}
