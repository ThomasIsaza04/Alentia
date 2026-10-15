import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { enviarOEncolar } from "../offline/outbox.js";
import { useSesion } from "../sesion.jsx";
import { zonaDelNavegador } from "./Salud.jsx";

// Recordatorios dentro de la app (RF-NOT-01 se sustituye por recordatorios en la app; ver documento).
// Se consulta cada minuto mientras la app está abierta. Sin consentimiento de notificaciones, no aparece.

const ETIQUETA = { atrasada: "Atrasada" };

export default function Recordatorios() {
  const { usuario } = useSesion();
  const [datos, setDatos] = useState(null);
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setDatos(await api(`/api/v1/recordatorios?zona_horaria=${encodeURIComponent(zonaDelNavegador())}`));
    } catch {
      // Sin consentimiento o sin conexión: el banner simplemente no aparece.
      setDatos(null);
    }
  }, []);

  useEffect(() => {
    if (!usuario) return undefined;
    cargar();
    const intervalo = setInterval(cargar, 60000);
    window.addEventListener("alentia:tomas", cargar);
    return () => {
      clearInterval(intervalo);
      window.removeEventListener("alentia:tomas", cargar);
    };
  }, [usuario, cargar]);

  if (!usuario || !datos || datos.items.length === 0) return null;

  async function registrar(item, estado) {
    setOcupado(true);
    try {
      const { enviado } = await enviarOEncolar({
        ruta: `/api/v1/tomas/${item.toma_id}/registros`,
        cuerpo: { estado, id: crypto.randomUUID() },
        tipo: "toma",
        resumen: `${item.nombre} · ${item.hora_local}`,
      });
      setAviso(
        enviado
          ? `Recordatorio de ${item.nombre} registrado`
          : `Recordatorio de ${item.nombre} guardado sin conexión; se enviará al reconectar`
      );
      window.dispatchEvent(new Event("alentia:tomas"));
    } catch (e) {
      setAviso(e.message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="recordatorios" aria-label="Recordatorios de tomas" data-testid="recordatorios">
      <p className="ayuda">{datos.aviso}</p>
      {aviso && <p className="mensaje ok" role="status">{aviso}</p>}
      <ul className="lista">
        {datos.items.map((item) => (
          <li key={item.toma_id} data-testid="recordatorio" data-hora={item.hora_local}>
            <span>
              <strong>{item.hora_local}</strong> {item.nombre} · {item.dosis}
              {item.estado === "atrasada" && <span className="etiqueta"> · {ETIQUETA.atrasada}</span>}
            </span>
            <span className="acciones">
              <button disabled={ocupado} onClick={() => registrar(item, "tomada")}>Tomada</button>
              <button className="secundario" disabled={ocupado} onClick={() => registrar(item, "omitida")}>Omitida</button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
