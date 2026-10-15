// Cliente HTTP. El token de acceso vive solo en memoria (no en localStorage).
// El refresh token viaja en una cookie HttpOnly que JavaScript no puede leer.

let tokenDeAcceso = null;
let renovando = null;

export function fijarToken(token) {
  tokenDeAcceso = token;
}

export function tieneToken() {
  return tokenDeAcceso !== null;
}

export class ErrorApi extends Error {
  constructor(status, titulo, detalle) {
    super(detalle || titulo || "Error inesperado");
    this.status = status;
    this.titulo = titulo;
  }
}

async function leerError(respuesta) {
  try {
    const datos = await respuesta.json();
    return new ErrorApi(respuesta.status, datos.title, datos.detail);
  } catch {
    return new ErrorApi(respuesta.status, "Error", "No se pudo completar la acción");
  }
}

export async function renovarSesion() {
  // Varias peticiones pueden necesitar renovar a la vez: se comparte una sola llamada.
  if (!renovando) {
    renovando = fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" })
      .then(async (r) => {
        if (!r.ok) throw await leerError(r);
        const datos = await r.json();
        fijarToken(datos.access_token);
        return datos.access_token;
      })
      .finally(() => {
        renovando = null;
      });
  }
  return renovando;
}

export async function api(ruta, { metodo = "GET", cuerpo, sinSesion = false } = {}) {
  const enviar = () =>
    fetch(ruta, {
      method: metodo,
      credentials: "include",
      headers: {
        ...(cuerpo !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(tokenDeAcceso && !sinSesion ? { Authorization: `Bearer ${tokenDeAcceso}` } : {}),
      },
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    });

  let respuesta = await enviar();
  // Si el token venció, se renueva una vez con la cookie y se repite la petición.
  if (respuesta.status === 401 && !sinSesion && ruta !== "/api/v1/auth/refresh") {
    try {
      await renovarSesion();
      respuesta = await enviar();
    } catch {
      fijarToken(null);
    }
  }
  if (!respuesta.ok) throw await leerError(respuesta);
  if (respuesta.status === 204) return null;
  return respuesta.json();
}

// Descarga autenticada (exportación de datos): devuelve un Blob, no JSON.
export async function descargar(ruta) {
  const enviar = () =>
    fetch(ruta, {
      credentials: "include",
      headers: tokenDeAcceso ? { Authorization: `Bearer ${tokenDeAcceso}` } : {},
    });
  let respuesta = await enviar();
  if (respuesta.status === 401) {
    await renovarSesion();
    respuesta = await enviar();
  }
  if (!respuesta.ok) throw await leerError(respuesta);
  return respuesta.blob();
}
