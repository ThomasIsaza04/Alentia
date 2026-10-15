// Prueba e2e del acceso temporal (paso 7): titular genera QR y PIN, profesional sin cuenta
// ve solo lo elegido, un PIN incorrecto se cuenta, y la revocación corta la sesión.
// Requiere backend en 127.0.0.1:8000 (BACKEND_LOG) y Vite en 127.0.0.1:5173.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const correo = `acceso.${Date.now().toString(36)}@ejemplo.co`;
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

// Acepta las tres finalidades en la pantalla de inicio (paso 8). Sin salud aceptada no se registran datos.
async function aceptarConsentimiento(pagina) {
  const aviso = pagina.getByTestId("aviso-consentimiento");
  await aviso.waitFor();
  await aviso.locator("input[name=salud]").check();
  await aviso.locator("input[name=notificaciones]").check();
  await aviso.locator("input[name=qr]").check();
  await aviso.getByRole("button", { name: "Aceptar y continuar" }).click();
  await aviso.waitFor({ state: "detached" });
}

function vigilar(pagina, nombre) {
  pagina.on("pageerror", (e) => errores.push(`[${nombre}] pageerror: ${e.message}`));
  pagina.on("console", (m) => {
    // Los 401 y 404 esperados (PIN incorrecto, enlace usado, sesión revocada) se comprueban en la prueba.
    if (m.type() === "error" && !m.text().includes("Failed to load resource")) {
      errores.push(`[${nombre}] console: ${m.text()}`);
    }
  });
}

const navegador = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const opciones = { viewport: { width: 1000, height: 800 }, locale: "es-CO", timezoneId: "America/Bogota" };
const contextoTitular = await navegador.newContext(opciones);
const contextoProfesional = await navegador.newContext(opciones);
const t = await contextoTitular.newPage();
const pr = await contextoProfesional.newPage();
t.setDefaultTimeout(8000);
pr.setDefaultTimeout(8000);
vigilar(t, "titular");
vigilar(pr, "profesional");

try {
  console.log("Titular: cuenta, perfil y pauta");
  await t.goto(`${BASE}/registro`);
  await t.fill("input[name=correo]", correo);
  await t.fill("input[name=clave]", CLAVE);
  await t.click("button[type=submit]");
  await t.getByText("Si los datos son válidos").waitFor();
  const token = await esperarEnlaceVerificacion(correo);
  await t.goto(`${BASE}/verificar?token=${token}`);
  await t.getByText("Correo verificado").waitFor();
  await t.goto(`${BASE}/login`);
  await t.fill("input[name=correo]", correo);
  await t.fill("input[name=clave]", CLAVE);
  await t.click("button[type=submit]");
  await t.getByRole("heading", { name: "Mis perfiles" }).waitFor();
  await aceptarConsentimiento(t);

  await t.fill('form[data-testid="form-crear-perfil"] input[name=nombre]', "Carlos Ruiz");
  await t.fill('form[data-testid="form-crear-perfil"] input[name=fecha_nacimiento]', "1970-05-20");
  await t.click('form[data-testid="form-crear-perfil"] button[type=submit]');
  await t.getByText('Perfil "Carlos Ruiz" creado').waitFor();
  await t.getByRole("link", { name: "Carlos Ruiz" }).click();
  await t.getByTestId("titulo-perfil").waitFor();
  await t.getByTestId("enlace-medicacion").click();
  await t.getByTestId("titulo-salud").getByText("Medicación").waitFor();
  await t.fill('form[data-testid="form-medicamento"] input[name=nombre]', "Losartán");
  await t.fill('form[data-testid="form-medicamento"] input[name=dosis]', "50 mg");
  await t.click('form[data-testid="form-medicamento"] button[type=submit]');
  await t.getByText("Pauta creada").waitFor();
  ok("perfil y pauta creados");

  console.log("Titular: generar acceso solo con medicamentos");
  await t.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Medicación" }).click();
  await t.goto(t.url().replace(/\/medicacion$/, "/acceso"));
  await t.getByRole("heading", { name: "Acceso para profesional" }).waitFor();
  await t.getByRole("checkbox", { name: "Diagnósticos vigentes" }).uncheck();
  await t.getByRole("radio", { name: "15 minutos" }).check();
  await t.click('form[data-testid="form-acceso"] button[type=submit]');
  await t.getByTestId("acceso-generado").waitFor();
  const qrSrc = await t.getByTestId("qr").getAttribute("src");
  if (!qrSrc || !qrSrc.startsWith("data:image")) throw new Error("El QR no se generó");
  const pin = (await t.getByTestId("pin").textContent()).trim();
  if (!/^\d{6}$/.test(pin)) throw new Error(`PIN inválido: ${pin}`);
  const enlace = await t.getByTestId("enlace").inputValue();
  ok("QR y PIN de 6 dígitos generados");

  console.log("Profesional: sin cuenta, PIN incorrecto y luego correcto");
  await pr.goto(enlace);
  await pr.getByTestId("form-pin").waitFor();
  const incorrecto = pin === "000000" ? "111111" : "000000";
  await pr.fill('form[data-testid="form-pin"] input[name=pin]', incorrecto);
  await pr.click('form[data-testid="form-pin"] button[type=submit]');
  await pr.getByText("Te quedan 4 intentos").waitFor();
  ok("un PIN incorrecto muestra los intentos restantes");

  await pr.fill('form[data-testid="form-pin"] input[name=pin]', pin);
  await pr.click('form[data-testid="form-pin"] button[type=submit]');
  await pr.getByTestId("resumen-profesional").waitFor();
  await pr.getByTestId("seccion-medicamentos").getByText("Losartán").waitFor();
  const diagnosticos = await pr.getByTestId("seccion-diagnosticos").count();
  if (diagnosticos !== 0) throw new Error("Se mostró una categoría no elegida");
  await pr.getByTestId("aviso-origen").getByText("Datos aportados por el paciente").waitFor();
  ok("con el PIN correcto solo aparecen las categorías elegidas y el aviso de origen");
  await pr.screenshot({ path: path.join(SHOTS, "profesional-resumen.png"), fullPage: true });

  console.log("Titular: bitácora y revocación");
  await t.reload();
  await t.getByTestId("acceso-temporal").first().getByRole("button", { name: "Bitácora" }).click();
  const bitacora = t.getByTestId("bitacora");
  await bitacora.getByText("PIN incorrecto").waitFor();
  await bitacora.getByText("PIN correcto, acceso iniciado").waitFor();
  ok("la bitácora registra el PIN incorrecto y el acceso iniciado");

  await t.getByTestId("acceso-temporal").first().getByRole("button", { name: "Revocar" }).click();
  await t.getByText("Acceso revocado").waitFor();
  await t.getByTestId("estado-acceso").getByText("Revocado").waitFor();
  ok("el titular revoca el acceso");

  console.log("Profesional: la sesión deja de funcionar");
  await pr.getByRole("button", { name: "Actualizar" }).click();
  await pr.getByText("El paciente revocó este acceso").waitFor();
  ok("tras la revocación, la siguiente acción del profesional queda bloqueada");

  const nuevo = await contextoProfesional.newPage();
  vigilar(nuevo, "profesional-nuevo");
  await nuevo.goto(enlace);
  await nuevo.getByText("Este acceso no está disponible").waitFor();
  ok("el enlace ya no se puede abrir");
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await t.screenshot({ path: path.join(SHOTS, "fallo-acceso-titular.png"), fullPage: true }).catch(() => {});
  await pr.screenshot({ path: path.join(SHOTS, "fallo-acceso-profesional.png"), fullPage: true }).catch(() => {});
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
