// Prueba e2e del modo sin conexión (RF-PWA-01 a RF-PWA-03).
// Usa la vista previa de producción: en desarrollo no se registra el service worker.
// Requiere backend en 127.0.0.1:8000 (log en BACKEND_LOG) y `npx vite preview` en 127.0.0.1:4173.
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE_URL || "http://127.0.0.1:4173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const correo = `offline.${Date.now().toString(36)}@ejemplo.co`;
const errores = [];
const pasos = [];
const VITE = fileURLToPath(new URL("../node_modules/vite/bin/vite.js", import.meta.url));

// La vista previa la gestiona la propia prueba: detenerla simula una red caída también para el service worker,
// que con context.setOffline seguiría alcanzando el servidor.
function iniciarVistaPrevia() {
  return spawn(process.execPath, [VITE, "preview", "--host", "127.0.0.1", "--port", "4173", "--strictPort"], {
    stdio: "ignore",
  });
}

async function esperarVistaPrevia() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(BASE);
      if (r.ok) return;
    } catch {
      // Aún no escucha.
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("La vista previa no arrancó en 127.0.0.1:4173");
}

function detenerVistaPrevia(proceso) {
  return new Promise((resolver) => {
    if (!proceso || proceso.exitCode !== null) return resolver();
    proceso.once("exit", () => resolver());
    proceso.kill("SIGTERM");
  });
}

fs.mkdirSync(SHOTS, { recursive: true });
const ok = (msg) => { pasos.push(msg); console.log(`  ✔ ${msg}`); };

async function esperarEnlaceVerificacion(correoBuscado) {
  for (let i = 0; i < 40; i++) {
    const lineas = fs.readFileSync(LOG, "utf8").split("\n")
      .filter((l) => l.includes(`para ${correoBuscado}:`) && l.includes("verificar?token="));
    if (lineas.length) return lineas.at(-1).match(/token=([A-Za-z0-9_-]+)/)[1];
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`No apareció el enlace de verificación para ${correoBuscado}`);
}

async function aceptarConsentimiento(pagina) {
  const aviso = pagina.getByTestId("aviso-consentimiento");
  await aviso.waitFor();
  await aviso.locator("input[name=salud]").check();
  await aviso.locator("input[name=notificaciones]").check();
  await aviso.locator("input[name=qr]").check();
  await aviso.getByRole("button", { name: "Aceptar y continuar" }).click();
  await aviso.waitFor({ state: "detached" });
}

function vigilar(pagina) {
  pagina.on("pageerror", (e) => errores.push(`pageerror: ${e.message}`));
  pagina.on("console", (m) => {
    const texto = m.text();
    // Los fallos de red esperados (sin conexión) no son errores de la aplicación.
    if (m.type() === "error" && !/Failed to load resource|Failed to fetch|net::ERR_/.test(texto)) {
      errores.push(`console: ${texto}`);
    }
  });
}

const navegador = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const contexto = await navegador.newContext({
  viewport: { width: 1000, height: 800 },
  locale: "es-CO",
  timezoneId: "America/Bogota",
});
const p = await contexto.newPage();
p.setDefaultTimeout(8000);
vigilar(p);

let vistaPrevia = null;
try {
  vistaPrevia = iniciarVistaPrevia();
  await esperarVistaPrevia();

  console.log("Cuenta y perfil");
  await p.goto(`${BASE}/registro`);
  await p.fill("input[name=correo]", correo);
  await p.fill("input[name=clave]", CLAVE);
  await p.click("button[type=submit]");
  await p.getByText("Si los datos son válidos").waitFor();
  const token = await esperarEnlaceVerificacion(correo);
  await p.goto(`${BASE}/verificar?token=${token}`);
  await p.getByText("Correo verificado").waitFor();
  await p.goto(`${BASE}/login`);
  await p.fill("input[name=correo]", correo);
  await p.fill("input[name=clave]", CLAVE);
  await p.click("button[type=submit]");
  await p.getByRole("heading", { name: "Mis perfiles" }).waitFor();
  await aceptarConsentimiento(p);

  await p.fill('form[data-testid="form-crear-perfil"] input[name=nombre]', "Carlos Ruiz");
  await p.fill('form[data-testid="form-crear-perfil"] input[name=fecha_nacimiento]', "1970-05-20");
  await p.click('form[data-testid="form-crear-perfil"] button[type=submit]');
  await p.getByText('Perfil "Carlos Ruiz" creado').waitFor();
  await p.getByRole("link", { name: "Carlos Ruiz" }).click();
  await p.getByTestId("titulo-perfil").waitFor();
  const idPerfil = p.url().split("/perfiles/")[1];

  await p.getByTestId("enlace-medicacion").click();
  await p.getByTestId("titulo-salud").getByText("Medicación").waitFor();
  await p.fill('form[data-testid="form-medicamento"] input[name=nombre]', "Losartán");
  await p.fill('form[data-testid="form-medicamento"] input[name=dosis]', "50 mg");
  await p.fill('form[data-testid="form-medicamento"] input[name=horas]', "08:00, 20:00");
  await p.click('form[data-testid="form-medicamento"] button[type=submit]');
  await p.getByText("Pauta creada").waitFor();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).waitFor();
  ok("perfil con una pauta creada en línea");

  console.log("Service worker, manifiesto y caché");
  await p.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 20000 });
  const manifiesto = await p.evaluate(async () => {
    const r = await fetch("/manifest.webmanifest");
    return r.ok ? (await r.json()).name : null;
  });
  if (manifiesto !== "Alentia") throw new Error(`Manifiesto inesperado: ${manifiesto}`);
  ok("service worker activo y manifiesto disponible");

  // Se visitan las pantallas en línea para que sus datos queden en la caché.
  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Síntomas" }).click();
  await p.getByTestId("titulo-salud").getByText("Síntomas").waitFor();
  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Medicación" }).click();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).waitFor();
  ok("pantallas visitadas en línea");

  console.log("Sin conexión");
  await contexto.setOffline(true);
  await detenerVistaPrevia(vistaPrevia);
  await p.reload();
  await p.getByTestId("sin-conexion").waitFor();
  const tomas = p.getByTestId("tomas-hoy").getByTestId("toma");
  await tomas.nth(0).waitFor();
  ok("la app abre sin conexión con la sesión del último inicio y las tomas guardadas");

  await tomas.nth(0).getByRole("button", { name: "Tomada" }).click();
  await p.getByTestId("pendientes").getByText("1 registro pendiente").waitFor();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).getByTestId("estado-toma")
    .getByText("Tomada (sin enviar)").waitFor();
  ok("una toma registrada sin conexión queda pendiente y se muestra como tal");

  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Síntomas" }).click();
  await p.getByTestId("titulo-salud").getByText("Síntomas").waitFor();
  await p.fill('form[data-testid="form-sintoma"] input[name=sintoma]', "Mareo sin conexión");
  await p.fill('form[data-testid="form-sintoma"] input[name=intensidad]', "4");
  await p.click('form[data-testid="form-sintoma"] button[type=submit]');
  await p.getByTestId("sintoma-pendiente").getByText("Mareo sin conexión").waitFor();
  await p.getByTestId("pendientes").getByText("2 registros pendientes").waitFor();
  ok("un síntoma sin conexión aparece como pendiente");

  await p.reload();
  await p.getByTestId("pendientes").getByText("2 registros pendientes").waitFor();
  ok("los pendientes sobreviven a una recarga sin conexión");

  console.log("Reconexión y envío");
  vistaPrevia = iniciarVistaPrevia();
  await esperarVistaPrevia();
  await contexto.setOffline(false);
  await p.getByTestId("pendientes").waitFor({ state: "detached", timeout: 40000 });
  ok("al volver la conexión se envían los pendientes");

  await p.reload();
  await p.getByTestId("lista-sintomas").getByTestId("sintoma").getByText("Mareo sin conexión").waitFor();
  const cuantos = await p.getByTestId("lista-sintomas").getByTestId("sintoma")
    .filter({ hasText: "Mareo sin conexión" }).count();
  if (cuantos !== 1) throw new Error(`El síntoma se guardó ${cuantos} veces; debía ser una`);
  ok("el síntoma llega al servidor una sola vez");

  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Medicación" }).click();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).getByTestId("estado-toma")
    .getByText("Tomada", { exact: true }).waitFor();
  ok("la toma llega al servidor y ya no aparece como pendiente");
  await p.screenshot({ path: path.join(SHOTS, "offline-medicacion.png"), fullPage: true });

  console.log("Rechazo del servidor");
  await p.evaluate(async () => {
    const base = await new Promise((resolver, rechazar) => {
      const r = indexedDB.open("alentia-sin-conexion");
      r.onsuccess = () => resolver(r.result);
      r.onerror = () => rechazar(r.error);
    });
    await new Promise((resolver, rechazar) => {
      const tx = base.transaction("pendientes", "readwrite");
      tx.objectStore("pendientes").add({
        ruta: "/api/v1/tomas/00000000-0000-4000-8000-000000000000/registros",
        cuerpo: { estado: "tomada", id: crypto.randomUUID() },
        tipo: "toma",
        perfilId: null,
        resumen: "Toma inexistente",
        creado: new Date().toISOString(),
        rechazado: null,
      });
      tx.oncomplete = () => resolver();
      tx.onerror = () => rechazar(tx.error);
    });
    base.close();
    window.dispatchEvent(new Event("alentia:outbox"));
  });
  await p.getByTestId("rechazado").getByText("Toma inexistente").waitFor();
  await p.getByTestId("rechazado").getByText("Toma no encontrada").waitFor();
  ok("un registro que el servidor rechaza se muestra con su motivo");
  await p.getByTestId("rechazados").getByRole("button", { name: "Descartar" }).click();
  await p.getByTestId("rechazados").waitFor({ state: "detached" });
  ok("el registro rechazado se puede descartar");

  console.log("Cierre de sesión");
  await p.getByRole("button", { name: "Salir" }).click();
  await p.waitForURL(/\/login/);
  const restos = await p.evaluate(async () => ({
    cache: await caches.has("alentia-datos-v1"),
    usuario: localStorage.getItem("alentia.ultimoUsuario"),
  }));
  if (restos.cache || restos.usuario) throw new Error(`Quedaron datos tras cerrar sesión: ${JSON.stringify(restos)}`);
  ok("al cerrar sesión se borran las lecturas guardadas y el último usuario");
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await p.screenshot({ path: path.join(SHOTS, "fallo-offline.png"), fullPage: true }).catch(() => {});
} finally {
  await navegador.close();
  await detenerVistaPrevia(vistaPrevia);
}

console.log(`\n${pasos.length} comprobaciones superadas`);
if (errores.length) {
  console.log("Errores:");
  for (const e of errores) console.log(`  ✘ ${e}`);
  process.exit(1);
}
console.log("Sin errores en consola ni en la página.");
