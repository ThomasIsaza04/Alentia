import React, { useEffect, useState } from "react";
import { useSesion } from "./sesion.jsx";
import { descartarPendiente, sincronizar, usarPendientes } from "./offline/outbox.js";

// Estado de conexión, envíos pendientes y rechazados (RF-PWA-03).
const INTERVALO_REENVIO_MS = 30000;
const ETIQUETA_TIPO = { toma: "Toma", sintoma: "Síntoma" };

export function usarConexion() {
  const [conectado, setConectado] = useState(() => navigator.onLine);
  useEffect(() => {
    const encendido = () => setConectado(true);
    const apagado = () => setConectado(false);
    window.addEventListener("online", encendido);
    window.addEventListener("offline", apagado);
    return () => {
      window.removeEventListener("online", encendido);
      window.removeEventListener("offline", apagado);
    };
  }, []);
  return conectado;
}

export function EstadoConexion() {
  const { usuario } = useSesion();
  const conectado = usarConexion();
  const pendientes = usarPendientes();
  const [ocupado, setOcupado] = useState(false);

  const activos = pendientes.filter((p) => !p.rechazado);
  const rechazados = pendientes.filter((p) => p.rechazado);
  const hayActivos = activos.length > 0;

  // Reenvía al volver la red y, mientras haya pendientes, cada 30 segundos.
  useEffect(() => {
    if (!usuario || usuario.sinConexion || !conectado || !hayActivos) return undefined;
    sincronizar();
    const temporizador = setInterval(() => sincronizar(), INTERVALO_REENVIO_MS);
    return () => clearInterval(temporizador);
  }, [usuario, conectado, hayActivos]);

  if (!usuario) return null;
  if (conectado && !hayActivos && rechazados.length === 0) return null;

  async function enviarAhora() {
    setOcupado(true);
    try {
      await sincronizar();
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="conexion" aria-label="Estado de conexión" data-testid="estado-conexion">
      {!conectado && (
        <p role="status" data-testid="sin-conexion">
          <strong>Sin conexión.</strong> Se muestran los datos guardados en este dispositivo.
        </p>
      )}
      {hayActivos && (
        <p role="status" data-testid="pendientes">
          {activos.length === 1 ? "1 registro pendiente" : `${activos.length} registros pendientes`} de enviar.
          {conectado && (
            <button className="secundario" disabled={ocupado} onClick={enviarAhora}>
              Enviar ahora
            </button>
          )}
        </p>
      )}
      {rechazados.length > 0 && (
        <div role="alert" data-testid="rechazados">
          <p>
            {rechazados.length === 1
              ? "1 registro no se pudo guardar en el servidor."
              : `${rechazados.length} registros no se pudieron guardar en el servidor.`}
          </p>
          <ul className="lista">
            {rechazados.map((p) => (
              <li key={p.clave} data-testid="rechazado">
                <span>
                  <strong>{ETIQUETA_TIPO[p.tipo] || "Registro"}</strong>
                  {p.resumen ? ` · ${p.resumen}` : ""}
                  <br />
                  <small>{p.rechazado}</small>
                </span>
                <button className="secundario" onClick={() => descartarPendiente(p.clave)}>
                  Descartar
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
