import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, descargar } from "../api.js";
import { Mensaje, formatearFecha } from "../componentes.jsx";

// Consentimiento por finalidad, exportación y eliminación de la cuenta (paso 8).

export const ETIQUETAS_FINALIDAD = {
  salud: "Registro de salud (obligatorio para usar el registro)",
  notificaciones: "Notificaciones y recordatorios",
  qr: "Accesos temporales por QR para profesionales",
};

function guardarArchivo(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

// Aviso que aparece en la pantalla de inicio hasta que se acepta el tratamiento de datos de salud.
export function AvisoConsentimiento({ onAceptado }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    api("/api/v1/cuenta/consentimientos")
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, []);

  if (!datos) return null;
  if (datos.estado.salud.aceptado) return null;

  async function aceptar(evento) {
    evento.preventDefault();
    const datosForm = new FormData(evento.currentTarget);
    setError("");
    if (!datosForm.get("salud")) {
      setError("Para registrar datos de salud debes aceptar el tratamiento de datos de salud");
      return;
    }
    setOcupado(true);
    try {
      for (const finalidad of ["salud", "notificaciones", "qr"]) {
        if (datosForm.get(finalidad)) {
          await api("/api/v1/cuenta/consentimientos", {
            metodo: "POST",
            cuerpo: { finalidad, version: datos.politica.version, aceptado: true },
          });
        }
      }
      onAceptado?.();
      setDatos(await api("/api/v1/cuenta/consentimientos"));
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="tarjeta aviso" data-testid="aviso-consentimiento">
      <h2>Antes de registrar datos de salud</h2>
      <p className="ayuda">Versión de la política {datos.politica.version} · huella {datos.politica.hash.slice(0, 12)}</p>
      <Mensaje>{error}</Mensaje>
      <form onSubmit={aceptar} className="formulario">
        <label className="casilla">
          <input type="checkbox" name="salud" /> Acepto el tratamiento de mis datos de salud. {datos.politica.textos.salud}
        </label>
        <label className="casilla">
          <input type="checkbox" name="notificaciones" /> {datos.politica.textos.notificaciones}
        </label>
        <label className="casilla">
          <input type="checkbox" name="qr" /> {datos.politica.textos.qr}
        </label>
        <button type="submit" disabled={ocupado}>Aceptar y continuar</button>
      </form>
    </section>
  );
}

export default function MiCuenta() {
  const [consentimientos, setConsentimientos] = useState(null);
  const [eliminacion, setEliminacion] = useState(undefined);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setConsentimientos(await api("/api/v1/cuenta/consentimientos"));
      const e = await api("/api/v1/cuenta/eliminacion");
      setEliminacion(e.eliminar_en);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  async function cambiar(finalidad, aceptado) {
    setError("");
    setAviso("");
    try {
      await api("/api/v1/cuenta/consentimientos", {
        metodo: "POST",
        cuerpo: { finalidad, version: consentimientos.politica.version, aceptado },
      });
      setAviso(aceptado ? "Consentimiento aceptado" : "Consentimiento retirado");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function exportar(formato) {
    setError("");
    try {
      const blob = await descargar(`/api/v1/cuenta/exportacion?formato=${formato}`);
      guardarArchivo(blob, formato === "csv" ? "alentia-datos.csv" : "alentia-datos.json");
      setAviso(`Exportación ${formato.toUpperCase()} descargada`);
    } catch (e) {
      setError(e.message);
    }
  }

  async function solicitarEliminacion(evento) {
    evento.preventDefault();
    const clave = new FormData(evento.currentTarget).get("clave");
    setError("");
    setAviso("");
    setOcupado(true);
    try {
      const r = await api("/api/v1/cuenta/eliminacion", { metodo: "POST", cuerpo: { clave } });
      setEliminacion(r.eliminar_en);
      setAviso("Eliminación programada. Puedes cancelarla antes de la fecha indicada.");
      evento.currentTarget.reset();
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  }

  async function cancelarEliminacion() {
    setError("");
    try {
      await api("/api/v1/cuenta/eliminacion/cancelar", { metodo: "POST" });
      setEliminacion(null);
      setAviso("La eliminación fue cancelada");
    } catch (e) {
      setError(e.message);
    }
  }

  if (!consentimientos) return <p className="cargando">{error || "Cargando…"}</p>;

  return (
    <div className="pagina">
      <p><Link to="/">← Mis perfiles</Link></p>
      <h1>Mi cuenta</h1>
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      <section className="tarjeta">
        <h2>Consentimientos</h2>
        <p className="ayuda">Versión vigente {consentimientos.politica.version}. Cada cambio queda registrado.</p>
        <ul className="lista" data-testid="lista-consentimientos">
          {Object.keys(ETIQUETAS_FINALIDAD).map((finalidad) => {
            const estado = consentimientos.estado[finalidad];
            const obligatorio = finalidad === "salud";
            return (
              <li key={finalidad} data-testid={`consentimiento-${finalidad}`}>
                <span>{ETIQUETAS_FINALIDAD[finalidad]}</span>
                <span className="etiqueta">{estado.aceptado ? "Aceptado" : "No aceptado"}</span>
                {obligatorio ? (
                  <span className="ayuda">Para retirarlo, elimina tu cuenta.</span>
                ) : (
                  <button className="secundario" onClick={() => cambiar(finalidad, !estado.aceptado)}>
                    {estado.aceptado ? "Retirar" : "Aceptar"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="tarjeta">
        <h2>Exportar mis datos</h2>
        <p className="ayuda">Incluye tus perfiles como titular o representante, con sus registros y el historial de accesos. No incluye tokens ni contraseñas.</p>
        <div className="acciones">
          <button className="secundario" onClick={() => exportar("json")} data-testid="exportar-json">Descargar JSON</button>
          <button className="secundario" onClick={() => exportar("csv")} data-testid="exportar-csv">Descargar CSV</button>
        </div>
      </section>

      <section className="tarjeta">
        <h2>Eliminar mi cuenta</h2>
        {eliminacion ? (
          <>
            <p data-testid="eliminacion-programada">
              Tu cuenta se eliminará el <strong>{formatearFecha(eliminacion)}</strong> a las{" "}
              {new Date(eliminacion).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}.
            </p>
            <button className="secundario" onClick={cancelarEliminacion} data-testid="cancelar-eliminacion">
              Cancelar la eliminación
            </button>
          </>
        ) : (
          <form onSubmit={solicitarEliminacion} className="formulario" data-testid="form-eliminar">
            <p className="ayuda">
              Se borran los perfiles de los que eres titular, con todos sus registros, y los accesos de otras
              personas a esos perfiles. Tienes 7 días para cancelar antes de que se borren.
            </p>
            <label>Confirma con tu contraseña<input name="clave" type="password" required autoComplete="current-password" /></label>
            <button type="submit" className="peligro" disabled={ocupado}>Programar eliminación</button>
          </form>
        )}
      </section>
    </div>
  );
}
