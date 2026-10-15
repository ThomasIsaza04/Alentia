// Prueba e2e de sesión (pendientes del paso 3): recuperación de contraseña completa, renovación de
// token por 401 con cookie de refresco, y cierre cuando la cookie ya no existe.
// Requiere backend en 127.0.0.1:8000 (BACKEND_LOG) y Vite en 127.0.0.1:5173.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const NUEVA = "Clave-nueva-2026";
const correo = `sesion.${Date.now().toString(36)}@ejemplo.co`;
const errores = [];
const pasos = [];

fs.mkdirSync(SHOTS, { recursive: true });
const ok = (msg) => { pasos.push(msg); console.log(`  ✔ ${msg}`); };

async function esperarEnlace(correoBuscado, marca) {
  for (let i = 0; i < 40; i++) {
    const lineas = fs.readFileSync(LOG, "utf8").split("\n")
      .filter((l) => l.includes(`para ${correoBuscado}:`) && l.includes(marca));
    if (lineas.length) return lineas.at(-1).match(/token=([A-Za-z0-9_-]+)/)[1];
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`No apareció el enlace (${marca}) para ${correoBuscado}`);
}

const navegador = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const contexto = await navegador.newContext({ viewport: { width: 1000, height: 800 }, locale: "es-CO" });
const p = await contexto.newPage();
p.setDefaultTimeout(8000);
p.on("pageerror", (e) => errores.push(`pageerror: ${e.message}`));
p.on("console", (m) => {
  if (m.type() === "error" && !m.text().includes("Failed to load resource")) errores.push(`console: ${m.text()}`);
});

try {
  console.log("Registro, verificación e inicio de sesión");
  await p.goto(`${BASE}/registro`);
  await p.fill("input[name=correo]", correo);
  await p.fill("input[name=clave]", CLAVE);
  await p.click("button[type=submit]");
  await p.getByText("Si los datos son válidos").waitFor();
  await p.goto(`${BASE}/verificar?token=${await esperarEnlace(correo, "verificar?token=")}`);
  await p.getByText("Correo verificado").waitFor();
  await p.goto(`${BASE}/login`);
  await p.fill("input[name=correo]", correo);
  await p.fill("input[name=clave]", CLAVE);
  await p.click("button[type=submit]");
  await p.getByRole("heading", { name: "Mis perfiles" }).waitFor();

  console.log("Renovación de token ante un 401");
  let interceptada = false;
  let refrescos = 0;
  p.on("response", (r) => { if (r.url().endsWith("/api/v1/auth/refresh") && r.status() === 200) refrescos++; });
  await p.route("**/api/v1/perfiles", async (ruta) => {
    if (!interceptada) {
      interceptada = true;
      return ruta.fulfill({
        status: 401,
        contentType: "application/problem+json",
        body: JSON.stringify({ title: "Sesión no válida", status: 401, detail: "La sesión expiró" }),
      });
    }
    return ruta.continue();
  });
  await p.reload();
  await p.getByRole("heading", { name: "Mis perfiles" }).waitFor();
  if (!interceptada) throw new Error("No se interceptó la petición de perfiles");
  if (refrescos < 1) throw new Error("No se renovó la sesión con la cookie de refresco");
  await p.unroute("**/api/v1/perfiles");
  ok("un 401 renueva la sesión con la cookie y repite la petición");

  console.log("Recuperación de contraseña");
  await contexto.clearCookies();
  await p.goto(`${BASE}/recuperar`);
  await p.fill("input[name=correo]", correo);
  await p.click("button[type=submit]");
  await p.getByRole("status").waitFor();
  const enlaceRecuperacion = await esperarEnlace(correo, "restablecer?token=");
  ok("solicitar recuperación muestra el mensaje y envía el enlace");

  await p.goto(`${BASE}/restablecer?token=${enlaceRecuperacion}`);
  await p.fill("input[name=clave]", NUEVA);
  await p.click("button[type=submit]");
  await p.waitForTimeout(1000);
  ok("el enlace de recuperación acepta la nueva contraseña");

  await p.goto(`${BASE}/login`);
  await p.fill("input[name=correo]", correo);
  await p.fill("input[name=clave]", CLAVE);
  await p.click("button[type=submit]");
  await p.getByRole("alert").getByText("Correo o contraseña incorrectos").waitFor();
  ok("la contraseña anterior ya no funciona");

  await p.fill("input[name=clave]", NUEVA);
  await p.click("button[type=submit]");
  await p.getByRole("heading", { name: "Mis perfiles" }).waitFor();
  ok("la contraseña nueva inicia sesión");

  const reuso = await esperarEnlace(correo, "restablecer?token=").catch(() => null);
  await p.goto(`${BASE}/restablecer?token=${enlaceRecuperacion}`);
  await p.fill("input[name=clave]", "Otra-clave-2026");
  await p.click("button[type=submit]");
  await p.getByRole("alert").waitFor();
  ok("un enlace de recuperación ya usado no se puede reutilizar");

  console.log("Cierre de sesión sin cookie de refresco");
  await contexto.clearCookies();
  await p.goto(`${BASE}/`);
  await p.waitForURL(/\/login/);
  ok("sin cookie de refresco, la página privada redirige a iniciar sesión");
  await p.screenshot({ path: path.join(SHOTS, "sesion-login.png"), fullPage: true });
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await p.screenshot({ path: path.join(SHOTS, "fallo-sesion.png"), fullPage: true }).catch(() => {});
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
