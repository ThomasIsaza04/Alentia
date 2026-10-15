// Prueba e2e de recordatorios (paso 9): toma atrasada, banner de recordatorios y calendario .ics.
// Requiere backend en 127.0.0.1:8000 (BACKEND_LOG) y Vite en 127.0.0.1:5173.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const correo = `recordatorios.${Date.now().toString(36)}@ejemplo.co`;
const errores = [];
const pasos = [];

fs.mkdirSync(SHOTS, { recursive: true });
const ok = (msg) => { pasos.push(msg); console.log(`  ✔ ${msg}`); };
const omitido = (msg) => console.log(`  ➜ omitido: ${msg}`);

const horaBogota = (desplazamientoHoras) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit", hour12: false })
    .format(new Date(Date.now() + desplazamientoHoras * 3600e3));

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
const contexto = await navegador.newContext({ viewport: { width: 1000, height: 800 }, locale: "es-CO", timezoneId: "America/Bogota", acceptDownloads: true });
const p = await contexto.newPage();
p.setDefaultTimeout(8000);
p.on("pageerror", (e) => errores.push(`pageerror: ${e.message}`));
p.on("console", (m) => {
  if (m.type() === "error" && !m.text().includes("Failed to load resource")) errores.push(`console: ${m.text()}`);
});

try {
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

  const aviso = p.getByTestId("aviso-consentimiento");
  await aviso.waitFor();
  await aviso.locator("input[name=salud]").check();
  await aviso.locator("input[name=notificaciones]").check();
  await aviso.locator("input[name=qr]").check();
  await aviso.getByRole("button", { name: "Aceptar y continuar" }).click();
  await aviso.waitFor({ state: "detached" });

  await p.fill('form[data-testid="form-crear-perfil"] input[name=nombre]', "Rosa Díaz");
  await p.fill('form[data-testid="form-crear-perfil"] input[name=fecha_nacimiento]', "1955-03-02");
  await p.click('form[data-testid="form-crear-perfil"] button[type=submit]');
  await p.getByText('Perfil "Rosa Díaz" creado').waitFor();
  await p.getByRole("link", { name: "Rosa Díaz" }).click();
  await p.getByTestId("titulo-perfil").waitFor();
  await p.getByTestId("enlace-medicacion").click();
  await p.getByTestId("titulo-salud").getByText("Medicación").waitFor();

  // Una hora 3 horas antes de ahora (hora de Bogotá). Solo se puede probar si no cruza la medianoche.
  const hora = horaBogota(-3);
  const cruzaMedianoche = Number(horaBogota(0).slice(0, 2)) < 3;
  if (cruzaMedianoche) {
    omitido("la hora de hace 3 horas cae en el día anterior; la prueba de atraso se repite después de las 03:00");
  } else {
    await p.fill('form[data-testid="form-medicamento"] input[name=nombre]', "Enalapril");
    await p.fill('form[data-testid="form-medicamento"] input[name=dosis]', "10 mg");
    await p.fill('form[data-testid="form-medicamento"] input[name=horas]', hora);
    await p.click('form[data-testid="form-medicamento"] button[type=submit]');
    await p.getByText("Pauta creada").waitFor();

    const toma = p.getByTestId("tomas-hoy").getByTestId("toma").filter({ hasText: "Enalapril" });
    await toma.getByTestId("estado-toma").getByText("Atrasada").waitFor();
    ok(`la toma de las ${hora} aparece como atrasada`);

    const recordatorio = p.getByTestId("recordatorios").getByTestId("recordatorio").filter({ hasText: "Enalapril" });
    await recordatorio.waitFor();
    ok("el banner de recordatorios muestra la toma vencida");
    await p.getByTestId("recordatorios").getByText("no reemplaza la indicación médica").waitFor();
    ok("el banner incluye el aviso de límites");

    await recordatorio.getByRole("button", { name: "Tomada" }).click();
    await p.getByTestId("recordatorios").getByText("Recordatorio de Enalapril registrado").waitFor();
    await p.getByTestId("recordatorios").getByTestId("recordatorio").filter({ hasText: "Enalapril" }).waitFor({ state: "detached" });
    await toma.getByTestId("estado-toma").getByText("Tomada").waitFor();
    ok("registrar desde el banner quita el recordatorio y marca la toma");
  }

  await p.screenshot({ path: path.join(SHOTS, "recordatorios.png"), fullPage: true });

  const [descarga] = await Promise.all([
    p.waitForEvent("download"),
    p.getByTestId("descargar-ics").click(),
  ]);
  const ruta = await descarga.path();
  const ics = fs.readFileSync(ruta, "utf8");
  if (!ics.startsWith("BEGIN:VCALENDAR") || !ics.includes("BEGIN:VEVENT") || !ics.includes("no reemplaza la indicación médica")) {
    throw new Error("El archivo .ics no contiene los eventos esperados");
  }
  ok("el calendario .ics se descarga con eventos, alarmas y aviso");
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await p.screenshot({ path: path.join(SHOTS, "fallo-recordatorios.png"), fullPage: true }).catch(() => {});
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
