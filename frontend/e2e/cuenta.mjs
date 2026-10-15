// Prueba e2e de la cuenta (paso 8): consentimiento, exportación y eliminación con período de gracia.
// Requiere backend en 127.0.0.1:8000 (BACKEND_LOG) y Vite en 127.0.0.1:5173.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const correo = `cuenta.${Date.now().toString(36)}@ejemplo.co`;
const errores = [];
const pasos = [];

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

const navegador = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const contexto = await navegador.newContext({ viewport: { width: 1000, height: 800 }, locale: "es-CO", timezoneId: "America/Bogota" });
const p = await contexto.newPage();
p.setDefaultTimeout(8000);
p.on("pageerror", (e) => errores.push(`pageerror: ${e.message}`));
p.on("console", (m) => {
  if (m.type() === "error" && !m.text().includes("Failed to load resource")) errores.push(`console: ${m.text()}`);
});

try {
  console.log("Cuenta: registro, verificación e inicio de sesión");
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

  console.log("Consentimiento");
  const aviso = p.getByTestId("aviso-consentimiento");
  await aviso.waitFor();
  await aviso.getByRole("button", { name: "Aceptar y continuar" }).click();
  await aviso.getByText("Para registrar datos de salud debes aceptar").waitFor();
  ok("no se puede continuar sin aceptar el tratamiento de datos de salud");
  await aviso.locator("input[name=salud]").check();
  await aviso.getByRole("button", { name: "Aceptar y continuar" }).click();
  await aviso.waitFor({ state: "detached" });
  ok("aceptar salud oculta el aviso de consentimiento");

  await p.getByRole("link", { name: "Mi cuenta" }).click();
  await p.getByRole("heading", { name: "Mi cuenta", exact: true }).waitFor();
  const salud = p.getByTestId("consentimiento-salud");
  await salud.getByText("Aceptado").waitFor();
  const notif = p.getByTestId("consentimiento-notificaciones");
  await notif.getByText("No aceptado").waitFor();
  await notif.getByRole("button", { name: "Aceptar" }).click();
  await notif.getByText("Aceptado").waitFor();
  ok("el consentimiento de notificaciones se puede aceptar después");
  await notif.getByRole("button", { name: "Retirar" }).click();
  await notif.getByText("No aceptado").waitFor();
  ok("el consentimiento de notificaciones se puede retirar");
  await salud.getByText("Para retirarlo, elimina tu cuenta.").waitFor();

  console.log("Exportación");
  const [descarga] = await Promise.all([
    p.waitForEvent("download"),
    p.getByTestId("exportar-json").click(),
  ]);
  if (!descarga.suggestedFilename().endsWith(".json")) throw new Error("La exportación JSON no se descargó");
  ok("la exportación JSON se descarga como archivo");
  const [csv] = await Promise.all([
    p.waitForEvent("download"),
    p.getByTestId("exportar-csv").click(),
  ]);
  if (!csv.suggestedFilename().endsWith(".csv")) throw new Error("La exportación CSV no se descargó");
  ok("la exportación CSV se descarga como archivo");

  console.log("Eliminación con período de gracia");
  const formulario = p.getByTestId("form-eliminar");
  await formulario.locator("input[name=clave]").fill("clave-equivocada-2026");
  await formulario.getByRole("button", { name: "Programar eliminación" }).click();
  await p.getByRole("alert").getByText("La contraseña no es correcta").waitFor();
  ok("una contraseña incorrecta no programa la eliminación");

  await formulario.locator("input[name=clave]").fill(CLAVE);
  await formulario.getByRole("button", { name: "Programar eliminación" }).click();
  await p.getByTestId("eliminacion-programada").waitFor();
  ok("la eliminación queda programada con fecha");
  await p.screenshot({ path: path.join(SHOTS, "mi-cuenta-eliminacion.png"), fullPage: true });

  await p.getByTestId("cancelar-eliminacion").click();
  await p.getByTestId("form-eliminar").waitFor();
  ok("cancelar la eliminación la quita");
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await p.screenshot({ path: path.join(SHOTS, "fallo-cuenta.png"), fullPage: true }).catch(() => {});
} finally {
  await navegador.close();
}

console.log(`\n${pasos.length} comprobaciones superadas`);
if (errores.length) {
  console.log("Errores:");
  for (const e of errores) console.log(`  ✘ ${e}`);
  process.exit(1);
}
console.log("Sin errores en consola ni en la página.");
