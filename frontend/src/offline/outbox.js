// Cola de envíos sin conexión (RF-PWA-02).
// Las tomas y síntomas que no llegan al servidor se guardan en IndexedDB (no en localStorage: pueden ser muchos).
// Cada registro lleva un identificador de cliente; el backend lo acepta dos veces sin duplicar (idempotente).
import { useEffect, useState } from "react";
import { api, ErrorApi } from "../api.js";

const BASE = "alentia-sin-conexion";
const TIENDA = "pendientes";
const CACHE_DATOS = "alentia-datos-v1";

function abrirBase() {
  return new Promise((resolver, rechazar) => {
    const peticion = indexedDB.open(BASE, 1);
    peticion.onupgradeneeded = () => {
      peticion.result.createObjectStore(TIENDA, { keyPath: "clave", autoIncrement: true });
    };
    peticion.onsuccess = () => resolver(peticion.result);
    peticion.onerror = () => rechazar(peticion.error);
  });
}

// Ejecuta una operación sobre la tienda y espera a que la transacción termine.
async function operar(modo, operacion) {
  const base = await abrirBase();
  return new Promise((resolver, rechazar) => {
    const transaccion = base.transaction(TIENDA, modo);
    const peticion = operacion(transaccion.objectStore(TIENDA));
    let resultado;
    peticion.onsuccess = () => {
      resultado = peticion.result;
    };
    transaccion.oncomplete = () => {
      base.close();
      resolver(resultado);
    };
    transaccion.onerror = () => {
      base.close();
      rechazar(transaccion.error);
    };
    transaccion.onabort = () => {
      base.close();
      rechazar(transaccion.error || new Error("Transacción cancelada"));
    };
  });
}

function avisarCambio() {
  window.dispatchEvent(new Event("alentia:outbox"));
}

export function listarPendientes() {
  return operar("readonly", (almacen) => almacen.getAll());
}

async function encolar(registro) {
  await operar("readwrite", (almacen) => almacen.add(registro));
  avisarCambio();
}

async function eliminar(clave) {
  await operar("readwrite", (almacen) => almacen.delete(clave));
  avisarCambio();
}

async function marcarRechazado(clave, motivo) {
  const actual = await operar("readonly", (almacen) => almacen.get(clave));
  if (actual) {
    await operar("readwrite", (almacen) => almacen.put({ ...actual, rechazado: motivo }));
  }
  avisarCambio();
}

// Envía un registro; si no hay red (o el servidor falla), lo guarda para reenviarlo después.
// Los errores de negocio (validación, permisos) se devuelven tal cual: no se encolan.
export async function enviarOEncolar({ ruta, cuerpo, tipo, perfilId, resumen }) {
  try {
    await api(ruta, { metodo: "POST", cuerpo });
    return { enviado: true };
  } catch (error) {
    if (error instanceof ErrorApi && error.status < 500) throw error;
    await encolar({
      ruta,
      cuerpo,
      tipo,
      perfilId: perfilId || null,
      resumen: resumen || "",
      creado: new Date().toISOString(),
      rechazado: null,
    });
    return { enviado: false };
  }
}

let sincronizando = null;

// Reenvía en orden. Se detiene ante fallos de red o del servidor (se reintenta luego);
// un rechazo definitivo (4xx) se conserva con su motivo para que la persona lo revise.
export function sincronizar() {
  if (!sincronizando) {
    sincronizando = hacerSincronizacion().finally(() => {
      sincronizando = null;
    });
  }
  return sincronizando;
}

async function hacerSincronizacion() {
  if (typeof navigator !== "undefined" && !navigator.onLine) return { enviados: 0 };
  let enviados = 0;
  const pendientes = await listarPendientes();
  for (const item of pendientes) {
    if (item.rechazado) continue;
    try {
      await api(item.ruta, { metodo: "POST", cuerpo: item.cuerpo });
      await eliminar(item.clave);
      enviados++;
    } catch (error) {
      const reintentable =
        !(error instanceof ErrorApi) ||
        error.status >= 500 ||
        [401, 408, 429].includes(error.status);
      if (reintentable) break;
      await marcarRechazado(item.clave, error.message);
    }
  }
  if (enviados > 0) window.dispatchEvent(new Event("alentia:tomas"));
  avisarCambio();
  return { enviados };
}

export function descartarPendiente(clave) {
  return eliminar(clave);
}

// Hook: lista de envíos pendientes o rechazados, actualizada en cada cambio.
export function usarPendientes() {
  const [lista, setLista] = useState([]);
  useEffect(() => {
    let vivo = true;
    const cargar = () => {
      listarPendientes()
        .then((datos) => vivo && setLista(datos))
        .catch(() => vivo && setLista([]));
    };
    cargar();
    window.addEventListener("alentia:outbox", cargar);
    return () => {
      vivo = false;
      window.removeEventListener("alentia:outbox", cargar);
    };
  }, []);
  return lista;
}

// Al cerrar sesión se borran las lecturas guardadas. Los envíos pendientes se conservan
// hasta que se sincronicen o se descarten.
export async function borrarCacheDatos() {
  try {
    await caches.delete(CACHE_DATOS);
  } catch {
    // Sin Cache Storage (p. ej. contexto no seguro): no hay nada que borrar.
  }
}
