import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Mensaje, formatearFecha } from "../componentes.jsx";
import { descargar } from "../api.js";
import { enviarOEncolar, usarPendientes } from "../offline/outbox.js";

// Pantallas de medicación (tomas), síntomas y diagnósticos (pasos 5 y 6).
// Las horas se muestran en la zona horaria del navegador; el backend guarda todo en UTC.

const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;
const ETIQUETA_ESTADO = { tomada: "Tomada", omitida: "Omitida", pospuesta: "Pospuesta", atrasada: "Atrasada" };
const ESTADOS_TOMA = ["tomada", "omitida", "pospuesta"];

// Avisa al banner de recordatorios que las tomas cambiaron (sin esperar al siguiente sondeo).
export function avisarTomas() {
  window.dispatchEvent(new Event("alentia:tomas"));
}

export function zonaDelNavegador() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Bogota";
}

// Fecha local YYYY-MM-DD, desplazada un número de días respecto a hoy.
export function fechaLocal(desplazamiento = 0) {
  const d = new Date();
  d.setDate(d.getDate() + desplazamiento);
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

// Identificador generado en el cliente: permite reenviar sin duplicar el registro.
function nuevoId() {
  return crypto.randomUUID();
}

function describirFrecuencia(f) {
  return f.tipo === "horarios"
    ? `A las ${f.horas.join(", ")}`
    : `Cada ${f.cada_horas} h desde las ${f.desde}`;
}

function formatearMomento(valor, zona) {
  return new Date(valor).toLocaleString("es-CO", {
    timeZone: zona,
    dateStyle: "short",
    timeStyle: "short",
  });
}

function usarPerfil(id) {
  const [perfil, setPerfil] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api(`/api/v1/perfiles/${id}`)
      .then(setPerfil)
      .catch((e) => setError(e.message));
  }, [id]);
  return { perfil, errorPerfil: error };
}

function EncabezadoSalud({ id, perfil, activa, titulo }) {
  const pestanas = [
    ["medicacion", "Medicación"],
    ["sintomas", "Síntomas"],
    ["diagnosticos", "Diagnósticos"],
  ];
  return (
    <>
      <p><Link to={`/perfiles/${id}`}>← {perfil.nombre}</Link></p>
      <h1 data-testid="titulo-salud">{titulo}</h1>
      <nav className="pestanas" aria-label="Registros de salud">
        {pestanas.map(([clave, texto]) => (
          <Link
            key={clave}
            to={`/perfiles/${id}/${clave}`}
            className={clave === activa ? "activa" : ""}
            aria-current={clave === activa ? "page" : undefined}
          >
            {texto}
          </Link>
        ))}
      </nav>
    </>
  );
}

function ErrorPagina({ mensaje, id }) {
  return (
    <div className="pagina">
      <Mensaje>{mensaje}</Mensaje>
      <Link to={id ? `/perfiles/${id}` : "/"}>Volver</Link>
    </div>
  );
}

// ---------- medicación ----------

export function Medicacion() {
  const { id } = useParams();
  const { perfil, errorPerfil } = usarPerfil(id);
  const zona = zonaDelNavegador();
  const hoy = fechaLocal();
  const [medicamentos, setMedicamentos] = useState([]);
  const [tomas, setTomas] = useState([]);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const pendientes = usarPendientes();

  // Tomas registradas en este dispositivo que aún no llegaron al servidor: se muestran como "sin enviar".
  const pendientesToma = new Map();
  for (const p of pendientes) {
    if (p.tipo === "toma" && !p.rechazado) pendientesToma.set(p.ruta.split("/")[4], p.cuerpo.estado);
  }

  const puedeEditar = perfil && (perfil.alcance === "editor" || perfil.alcance === "admin");

  const cargar = useCallback(async () => {
    try {
      setMedicamentos(await api(`/api/v1/perfiles/${id}/medicamentos`));
      setTomas(
        await api(
          `/api/v1/perfiles/${id}/tomas?desde=${hoy}&hasta=${hoy}&zona_horaria=${encodeURIComponent(zona)}`
        )
      );
    } catch (e) {
      setError(e.message);
    }
  }, [id, hoy, zona]);

  useEffect(() => {
    if (perfil) cargar();
  }, [perfil, cargar]);

  // Un registro hecho desde el banner de recordatorios también actualiza esta lista.
  useEffect(() => {
    window.addEventListener("alentia:tomas", cargar);
    return () => window.removeEventListener("alentia:tomas", cargar);
  }, [cargar]);

  // La acción puede devolver un texto de aviso propio (p. ej. "guardado sin conexión").
  async function ejecutar(accion, mensajeOk) {
    setError("");
    setAviso("");
    setOcupado(true);
    try {
      const resultado = await accion();
      const texto = (typeof resultado === "string" && resultado) || mensajeOk;
      if (texto) setAviso(texto);
      avisarTomas();
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  }

  async function crearPauta(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    let frecuencia;
    if (datos.get("tipo") === "horarios") {
      const horas = String(datos.get("horas") || "")
        .split(",")
        .map((h) => h.trim())
        .filter(Boolean);
      if (horas.length === 0 || !horas.every((h) => HORA.test(h))) {
        setError("Escribe las horas como HH:MM separadas por comas, por ejemplo 08:00, 20:00");
        return;
      }
      frecuencia = { tipo: "horarios", horas };
    } else {
      frecuencia = {
        tipo: "cada_horas",
        cada_horas: Number(datos.get("cada_horas")),
        desde: datos.get("desde"),
      };
    }
    const cuerpo = {
      nombre: datos.get("nombre"),
      dosis: datos.get("dosis"),
      frecuencia,
      inicio: datos.get("inicio"),
      zona_horaria: zona,
    };
    if (datos.get("fin")) cuerpo.fin = datos.get("fin");
    await ejecutar(async () => {
      await api(`/api/v1/perfiles/${id}/medicamentos`, { metodo: "POST", cuerpo });
      formulario.reset();
    }, "Pauta creada");
  }

  function registrar(toma, estado) {
    const mensajeOk = `Toma marcada como ${ETIQUETA_ESTADO[estado].toLowerCase()}`;
    return ejecutar(async () => {
      // El identificador se crea una sola vez: si el envío se repite, el servidor no duplica el registro.
      const { enviado } = await enviarOEncolar({
        ruta: `/api/v1/tomas/${toma.id}/registros`,
        cuerpo: { estado, id: nuevoId() },
        tipo: "toma",
        perfilId: id,
        resumen: `${toma.nombre} · ${toma.hora_local}`,
      });
      return enviado ? null : `${mensajeOk} sin conexión; se enviará al reconectar`;
    }, mensajeOk);
  }

  function cambiarActivo(medicamento) {
    return ejecutar(
      () =>
        api(`/api/v1/medicamentos/${medicamento.id}`, {
          metodo: "PATCH",
          cuerpo: { activo: !medicamento.activo },
        }),
      medicamento.activo ? "Pauta desactivada" : "Pauta reactivada"
    );
  }

  if (errorPerfil) return <ErrorPagina mensaje={errorPerfil} />;
  if (!perfil) return <p className="cargando">Cargando…</p>;

  return (
    <div className="pagina">
      <EncabezadoSalud id={id} perfil={perfil} activa="medicacion" titulo="Medicación" />
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      <section className="tarjeta">
        <h2>Tomas de hoy</h2>
        <p className="ayuda">
          {formatearFecha(hoy)} · horario de {zona}
        </p>
        {tomas.length === 0 && <p>No hay tomas programadas para hoy.</p>}
        <ul className="lista" data-testid="tomas-hoy">
          {tomas.map((t) => (
            <li key={t.id} data-testid="toma" data-hora={t.hora_local}>
              <span>
                <strong>{t.hora_local}</strong> {t.nombre} · {t.dosis}
              </span>
              <span className="etiqueta" data-testid="estado-toma">
                {pendientesToma.has(t.id)
                  ? `${ETIQUETA_ESTADO[pendientesToma.get(t.id)]} (sin enviar)`
                  : t.estado
                    ? ETIQUETA_ESTADO[t.estado]
                    : "Pendiente"}
              </span>
              {puedeEditar && (
                <span className="acciones">
                  {ESTADOS_TOMA.map((estado) => (
                    <button
                      key={estado}
                      className="secundario"
                      disabled={ocupado}
                      onClick={() => registrar(t, estado)}
                    >
                      {ETIQUETA_ESTADO[estado]}
                    </button>
                  ))}
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="tarjeta">
        <h2>Pautas</h2>
        {medicamentos.length === 0 && <p>No hay medicamentos registrados.</p>}
        <ul className="lista" data-testid="lista-medicamentos">
          {medicamentos.map((m) => (
            <li key={m.id} data-testid="medicamento">
              <span>
                <strong>{m.nombre}</strong> · {m.dosis}
                <br />
                <small>{describirFrecuencia(m.frecuencia)} · desde {formatearFecha(m.inicio)}</small>
              </span>
              {!m.activo && <span className="etiqueta">inactiva</span>}
              {puedeEditar && (
                <button className="secundario" disabled={ocupado} onClick={() => cambiarActivo(m)}>
                  {m.activo ? "Desactivar" : "Reactivar"}
                </button>
              )}
            </li>
          ))}
        </ul>

        <div className="acciones">
          <button
            className="secundario"
            data-testid="descargar-ics"
            onClick={async () => {
              try {
                const blob = await descargar(`/api/v1/perfiles/${id}/calendario.ics`);
                const url = URL.createObjectURL(blob);
                const enlace = document.createElement("a");
                enlace.href = url;
                enlace.download = "alentia-tomas.ics";
                document.body.appendChild(enlace);
                enlace.click();
                enlace.remove();
                URL.revokeObjectURL(url);
              } catch (e) {
                setError(e.message);
              }
            }}
          >
            Descargar calendario (.ics)
          </button>
        </div>

        {puedeEditar && (
          <>
            <h3>Nueva pauta</h3>
            <form onSubmit={crearPauta} className="formulario" data-testid="form-medicamento">
              <label>Nombre<input name="nombre" required maxLength={100} placeholder="Ej.: Losartán" /></label>
              <label>Dosis<input name="dosis" required maxLength={60} placeholder="Ej.: 50 mg" /></label>
              <fieldset className="grupo">
                <legend>Frecuencia</legend>
                <label className="casilla">
                  <input type="radio" name="tipo" value="horarios" defaultChecked /> Horas fijas
                </label>
                <label className="casilla">
                  <input type="radio" name="tipo" value="cada_horas" /> Cada N horas
                </label>
              </fieldset>
              <label>Horas del día (HH:MM, separadas por comas)<input name="horas" defaultValue="08:00, 20:00" /></label>
              <label>Cada cuántas horas<input name="cada_horas" type="number" min="1" max="24" defaultValue="8" /></label>
              <label>Desde la hora<input name="desde" type="time" defaultValue="06:00" /></label>
              <label>Inicio<input name="inicio" type="date" required defaultValue={hoy} /></label>
              <label>Fin (opcional)<input name="fin" type="date" /></label>
              <button type="submit" disabled={ocupado}>Guardar pauta</button>
            </form>
            <p className="ayuda">Las tomas se programan 30 días a partir del inicio.</p>
          </>
        )}
      </section>
    </div>
  );
}

// ---------- síntomas ----------

export function Sintomas() {
  const { id } = useParams();
  const { perfil, errorPerfil } = usarPerfil(id);
  const zona = zonaDelNavegador();
  const [registros, setRegistros] = useState([]);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const pendientes = usarPendientes().filter((p) => p.tipo === "sintoma" && p.perfilId === id);

  const puedeEditar = perfil && (perfil.alcance === "editor" || perfil.alcance === "admin");

  const cargar = useCallback(async () => {
    try {
      setRegistros(
        await api(
          `/api/v1/perfiles/${id}/sintomas?desde=${fechaLocal(-6)}&hasta=${fechaLocal()}&zona_horaria=${encodeURIComponent(zona)}`
        )
      );
    } catch (e) {
      setError(e.message);
    }
  }, [id, zona]);

  useEffect(() => {
    if (perfil) cargar();
  }, [perfil, cargar]);

  async function registrar(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    const cuerpo = {
      id: nuevoId(),
      sintoma: datos.get("sintoma"),
      intensidad: Number(datos.get("intensidad")),
    };
    if (datos.get("nota")) cuerpo.nota = datos.get("nota");
    // El campo datetime-local no trae zona: se convierte a instante UTC con Date.
    if (datos.get("fecha")) cuerpo.fecha = new Date(datos.get("fecha")).toISOString();
    setError("");
    setAviso("");
    try {
      const { enviado } = await enviarOEncolar({
        ruta: `/api/v1/perfiles/${id}/sintomas`,
        cuerpo,
        tipo: "sintoma",
        perfilId: id,
        resumen: `${cuerpo.sintoma} · ${cuerpo.intensidad}/10`,
      });
      formulario.reset();
      setAviso(enviado ? "Síntoma registrado" : "Síntoma guardado sin conexión; se enviará al reconectar");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  if (errorPerfil) return <ErrorPagina mensaje={errorPerfil} />;
  if (!perfil) return <p className="cargando">Cargando…</p>;

  return (
    <div className="pagina">
      <EncabezadoSalud id={id} perfil={perfil} activa="sintomas" titulo="Síntomas" />
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      {puedeEditar && (
        <section className="tarjeta">
          <h2>Registrar síntoma</h2>
          <form onSubmit={registrar} className="formulario" data-testid="form-sintoma">
            <label>Síntoma<input name="sintoma" required maxLength={100} placeholder="Ej.: Dolor de cabeza" /></label>
            <label>Intensidad (0 a 10)<input name="intensidad" type="number" min="0" max="10" required defaultValue="5" /></label>
            <label>Nota (opcional)<textarea name="nota" maxLength={500} rows={3} /></label>
            <label>Momento (opcional, por defecto ahora)<input name="fecha" type="datetime-local" /></label>
            <button type="submit">Guardar síntoma</button>
          </form>
        </section>
      )}

      <section className="tarjeta">
        <h2>Últimos 7 días</h2>
        {registros.length === 0 && <p>No hay síntomas registrados en este periodo.</p>}
        <ul className="lista" data-testid="lista-sintomas">
          {pendientes.map((p) => (
            <li key={p.clave} data-testid="sintoma-pendiente">
              <span>
                <strong>{p.cuerpo.sintoma}</strong> · intensidad {p.cuerpo.intensidad}/10
                <span className="etiqueta"> · sin enviar</span>
                <br />
                <small>{p.cuerpo.nota ? p.cuerpo.nota : "Pendiente de enviar al reconectar"}</small>
              </span>
            </li>
          ))}
          {registros.map((r) => (
            <li key={r.id} data-testid="sintoma">
              <span>
                <strong>{r.sintoma}</strong> · intensidad {r.intensidad}/10
                <br />
                <small>{formatearMomento(r.fecha, zona)}{r.nota ? ` · ${r.nota}` : ""}</small>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

// ---------- diagnósticos ----------

export function Diagnosticos() {
  const { id } = useParams();
  const { perfil, errorPerfil } = usarPerfil(id);
  const [zonas, setZonas] = useState([]);
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [mostrarResueltos, setMostrarResueltos] = useState(true);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const puedeEditar = perfil && (perfil.alcance === "editor" || perfil.alcance === "admin");

  const cargar = useCallback(async () => {
    try {
      setZonas(await api(`/api/v1/perfiles/${id}/zonas?incluir_archivadas=true`));
      setDiagnosticos(
        await api(`/api/v1/perfiles/${id}/diagnosticos?incluir_resueltos=${mostrarResueltos}`)
      );
    } catch (e) {
      setError(e.message);
    }
  }, [id, mostrarResueltos]);

  useEffect(() => {
    if (perfil) cargar();
  }, [perfil, cargar]);

  const nombreZona = (zonaId) => zonas.find((z) => z.id === zonaId)?.nombre;

  async function crear(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const datos = new FormData(formulario);
    const cuerpo = {
      descripcion: datos.get("descripcion"),
      fecha: datos.get("fecha"),
      zona_id: datos.get("zona_id") || null,
    };
    setError("");
    setAviso("");
    try {
      await api(`/api/v1/perfiles/${id}/diagnosticos`, { metodo: "POST", cuerpo });
      formulario.reset();
      setAviso("Diagnóstico registrado");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function cambiarEstado(diagnostico) {
    const estado = diagnostico.estado === "vigente" ? "resuelto" : "vigente";
    setError("");
    setAviso("");
    try {
      await api(`/api/v1/diagnosticos/${diagnostico.id}`, { metodo: "PATCH", cuerpo: { estado } });
      setAviso(estado === "resuelto" ? "Diagnóstico marcado como resuelto" : "Diagnóstico reabierto");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  if (errorPerfil) return <ErrorPagina mensaje={errorPerfil} />;
  if (!perfil) return <p className="cargando">Cargando…</p>;

  const zonasActivas = zonas.filter((z) => !z.archivada);

  return (
    <div className="pagina">
      <EncabezadoSalud id={id} perfil={perfil} activa="diagnosticos" titulo="Diagnósticos" />
      <Mensaje>{error}</Mensaje>
      <Mensaje tipo="ok">{aviso}</Mensaje>

      {puedeEditar && (
        <section className="tarjeta">
          <h2>Nuevo diagnóstico</h2>
          <form onSubmit={crear} className="formulario" data-testid="form-diagnostico">
            <label>Descripción<textarea name="descripcion" required maxLength={500} rows={3} /></label>
            <label>Fecha<input name="fecha" type="date" required defaultValue={fechaLocal()} /></label>
            <label>
              Zona de consulta (opcional)
              <select name="zona_id" defaultValue="">
                <option value="">Sin zona</option>
                {zonasActivas.map((z) => (
                  <option key={z.id} value={z.id}>{z.nombre}</option>
                ))}
              </select>
            </label>
            <button type="submit">Guardar diagnóstico</button>
          </form>
        </section>
      )}

      <section className="tarjeta">
        <h2>Historial</h2>
        <label className="casilla">
          <input type="checkbox" checked={mostrarResueltos} onChange={(e) => setMostrarResueltos(e.target.checked)} />
          Mostrar resueltos
        </label>
        {diagnosticos.length === 0 && <p>No hay diagnósticos para mostrar.</p>}
        <ul className="lista" data-testid="lista-diagnosticos">
          {diagnosticos.map((d) => (
            <li key={d.id} data-testid="diagnostico">
              <span>
                <strong>{d.descripcion}</strong>
                <br />
                <small>
                  {formatearFecha(d.fecha)}
                  {d.zona_id && nombreZona(d.zona_id) ? ` · ${nombreZona(d.zona_id)}` : ""}
                </small>
              </span>
              <span className="etiqueta" data-testid="estado-diagnostico">
                {d.estado === "vigente" ? "Vigente" : "Resuelto"}
              </span>
              {puedeEditar && (
                <button className="secundario" onClick={() => cambiarEstado(d)}>
                  {d.estado === "vigente" ? "Marcar resuelto" : "Reabrir"}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
