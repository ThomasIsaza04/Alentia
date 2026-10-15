import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import QRCode from "qrcode";
import { api } from "../api.js";
import { Mensaje, formatearFecha } from "../componentes.jsx";

// Titular: genera accesos temporales para un profesional (QR + PIN) y revisa su bitácora.

export const ETIQUETAS_CATEGORIA = {
  diagnosticos: "Diagnósticos vigentes",
  medicamentos: "Medicamentos activos",
  sintomas: "Síntomas recientes",
};

const ETIQUETAS_ESTADO = {
  pendiente: "Pendiente",
  consumido: "Usado",
  revocado: "Revocado",
  bloqueado: "Bloqueado por PIN",
  expirado: "Vencido",
};

const ETIQUETAS_EVENTO = {
  generado: "Generado",
  abierto: "Enlace abierto",
  pin_fallido: "PIN incorrecto",
  bloqueado: "Bloqueado tras 5 intentos",
  consumido: "PIN correcto, acceso iniciado",
  revocado: "Revocado por el titular",
};

const ETIQUETAS_DISPOSITIVO = { movil: "Móvil", escritorio: "Escritorio", desconocido: "Desconocido" };

function hora(valor) {
  return new Date(valor).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
}

export default function AccesoTemporal() {
  const { id } = useParams();
  const [perfil, setPerfil] = useState(null);
  const [accesos, setAccesos] = useState([]);
  const [nuevo, setNuevo] = useState(null);
  const [qr, setQr] = useState("");
  const [bitacoras, setBitacoras] = useState({});
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setAccesos(await api(`/api/v1/perfiles/${id}/accesos-temporales`));
    } catch (e) {
      setError(e.message);
    }
  }, [id]);

  useEffect(() => {
    api(`/api/v1/perfiles/${id}`).then(setPerfil).catch((e) => setError(e.message));
    cargar();
  }, [id, cargar]);

  // El QR codifica solo la dirección con el token. El PIN se entrega por separado.
  useEffect(() => {
    if (!nuevo) return;
    const url = `${window.location.origin}${nuevo.enlace_path}`;
    QRCode.toDataURL(url, { margin: 1, width: 240 }).then(setQr).catch(() => setQr(""));
  }, [nuevo]);

  async function crear(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    const categorias = datos.getAll("categorias");
    setError("");
    setAviso("");
    if (categorias.length === 0) {
      setError("Elige al menos una categoría para compartir");
      return;
    }
    setOcupado(true);
    try {
      const r = await api(`/api/v1/perfiles/${id}/accesos-temporales`, {
        metodo: "POST",
        cuerpo: { categorias, duracion_minutos: Number(datos.get("duracion_minutos")) },
      });
      setNuevo(r);
      setAviso("Acceso generado. El enlace y el PIN solo se muestran esta vez.");
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  }

  async function revocar(acceso) {
    setError("");
    setAviso("");
    try {
      await api(`/api/v1/accesos-temporales/${acceso.id}/revocar`, { metodo: "POST" });
      setAviso("Acceso revocado. El profesional deja de ver datos en su siguiente acción.");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function verBitacora(acceso) {
    try {
      const eventos = await api(`/api/v1/accesos-temporales/${acceso.id}/bitacora`);
      setBitacoras((previo) => ({ ...previo, [acceso.id]: eventos }));
    } catch (e) {
      setError(e.message);
    }
  }

  if (!perfil && !error) return <p className="cargando">Cargando…</p>;

  return (
    <div className="pagina">
      <p><Link to={`/perfiles/${id}`}>← {perfil ? perfil.nombre : "Perfil"}</Link></p>
      <h1>Acceso para profesional</h1>
      <p className="ayuda">
        Genera un código QR y un PIN de 6 dígitos. El profesional abre el enlace, escribe el PIN y ve solo
        las categorías que elijas, en modo lectura, durante el tiempo indicado.
      </p>
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      <section className="tarjeta">
        <h2>Generar acceso</h2>
        <form onSubmit={crear} className="formulario" data-testid="form-acceso">
          <fieldset className="grupo">
            <legend>Qué compartir</legend>
            {Object.entries(ETIQUETAS_CATEGORIA).map(([clave, texto]) => (
              <label key={clave} className="casilla">
                <input type="checkbox" name="categorias" value={clave} defaultChecked={clave !== "sintomas"} /> {texto}
              </label>
            ))}
          </fieldset>
          <fieldset className="grupo">
            <legend>Duración</legend>
            <label className="casilla"><input type="radio" name="duracion_minutos" value="15" defaultChecked /> 15 minutos</label>
            <label className="casilla"><input type="radio" name="duracion_minutos" value="30" /> 30 minutos</label>
          </fieldset>
          <button type="submit" disabled={ocupado}>Generar QR y PIN</button>
        </form>
      </section>

      {nuevo && (
        <section className="tarjeta" data-testid="acceso-generado">
          <h2>Entrega al profesional</h2>
          <div className="qr-bloque">
            {qr && <img src={qr} alt="Código QR del acceso temporal" width="240" height="240" data-testid="qr" />}
            <div>
              <p>PIN de 6 dígitos (dictar aparte del QR):</p>
              <p className="pin" data-testid="pin">{nuevo.pin}</p>
              <p className="ayuda">Vence a las {hora(nuevo.vence_en)}.</p>
              <p className="ayuda">Enlace (si el QR no se puede escanear):</p>
              <input readOnly value={`${window.location.origin}${nuevo.enlace_path}`} data-testid="enlace" onFocus={(e) => e.target.select()} />
            </div>
          </div>
        </section>
      )}

      <section className="tarjeta">
        <h2>Accesos emitidos</h2>
        {accesos.length === 0 && <p>Todavía no hay accesos.</p>}
        <ul className="lista" data-testid="lista-accesos-temporales">
          {accesos.map((a) => (
            <li key={a.id} data-testid="acceso-temporal" data-estado={a.estado}>
              <span>
                <strong>{a.categorias.map((c) => ETIQUETAS_CATEGORIA[c]).join(" · ")}</strong>
                <br />
                <small>{a.duracion_minutos} min · creado {formatearFecha(a.creado_en)} {hora(a.creado_en)}</small>
              </span>
              <span className="etiqueta" data-testid="estado-acceso">{ETIQUETAS_ESTADO[a.estado]}</span>
              <span className="acciones">
                {(a.estado === "pendiente" || a.estado === "consumido") && (
                  <button className="secundario peligro" onClick={() => revocar(a)}>Revocar</button>
                )}
                <button className="secundario" onClick={() => verBitacora(a)}>Bitácora</button>
              </span>
              {bitacoras[a.id] && (
                <ul className="bitacora" data-testid="bitacora">
                  {bitacoras[a.id].map((e, i) => (
                    <li key={i}>
                      {hora(e.ocurrido_en)} · {ETIQUETAS_EVENTO[e.tipo]} · {ETIQUETAS_DISPOSITIVO[e.tipo_dispositivo]}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
