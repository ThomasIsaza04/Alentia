// Service worker de Alentia (RF-PWA-01, RF-PWA-02).
// Vite lo genera en dist/sw.js y sustituye las marcas de versión y de lista de archivos (ver vite.config.js).
//
// Estrategias:
// - Cáscara de la app (HTML, JS, CSS, iconos): precarga en la instalación; los assets con hash se sirven desde caché.
// - Navegación: red primero; sin red, la página principal cacheada (la app es una SPA).
// - Lecturas de perfiles, medicación, síntomas y diagnósticos: red primero y copia en caché; sin red, la última copia.
// - Escrituras (POST, PATCH, DELETE): no se interceptan. Las gestiona el outbox de la aplicación.
// Los datos de salud en caché se borran al cerrar sesión (ver borrarCacheDatos en src/offline/outbox.js).

const VERSION = "__VERSION__";
const CACHE_SHELL = `alentia-shell-${VERSION}`;
const CACHE_DATOS = "alentia-datos-v1";
const ARCHIVOS_SHELL = __ARCHIVOS__;

// Rutas de datos que se guardan sin conexión. Las de acceso profesional, auth y exportaciones quedan fuera.
const RUTA_DATOS = /^\/api\/v1\/perfiles\//;
const RUTA_EXCLUIDA = /acceso|calendario\.ics|exportacion|\/auth\//;

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches
      .open(CACHE_SHELL)
      .then((cache) => cache.addAll(ARCHIVOS_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    (async () => {
      for (const nombre of await caches.keys()) {
        if (nombre.startsWith("alentia-shell-") && nombre !== CACHE_SHELL) {
          await caches.delete(nombre);
        }
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;
  const url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;

  if (peticion.mode === "navigate") {
    evento.respondWith(
      fetch(peticion).catch(() => caches.match("/", { cacheName: CACHE_SHELL }))
    );
    return;
  }

  if (ARCHIVOS_SHELL.includes(url.pathname) || url.pathname.startsWith("/assets/")) {
    evento.respondWith(caches.match(peticion).then((guardada) => guardada || fetch(peticion)));
    return;
  }

  if (RUTA_DATOS.test(url.pathname) && !RUTA_EXCLUIDA.test(url.pathname)) {
    evento.respondWith(redPrimeroConCopia(peticion));
  }
});

async function redPrimeroConCopia(peticion) {
  const cache = await caches.open(CACHE_DATOS);
  try {
    const respuesta = await fetch(peticion);
    if (respuesta.ok) cache.put(peticion, respuesta.clone());
    return respuesta;
  } catch {
    const guardada = await cache.match(peticion);
    if (guardada) return guardada;
    // Sin red y sin copia: la página lo muestra como error controlado, no como fallo de la app.
    return new Response(
      JSON.stringify({
        type: "about:blank",
        title: "Sin conexión",
        status: 503,
        detail: "No hay datos guardados en este dispositivo para esta consulta.",
      }),
      { status: 503, headers: { "Content-Type": "application/problem+json" } }
    );
  }
}
