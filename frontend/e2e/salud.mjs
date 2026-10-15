// Prueba e2e de medicación, tomas, síntomas y diagnósticos (pasos 5 y 6).
// Requiere backend en 127.0.0.1:8000 (log en BACKEND_LOG) y Vite en 127.0.0.1:5173.
// El navegador usa zona horaria America/Bogota: las tomas de 08:00 y 20:00 deben verse así.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const correo = `salud.${Date.now().toString(36)}@ejemplo.co`;
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

function vigilar(pagina) {
  pagina.on("pageerror", (e) => errores.push(`pageerror: ${e.message}`));
  pagina.on("console", (m) => {
    if (m.type() === "error" && !m.text().includes("Failed to load resource")) {
      errores.push(`console: ${m.text()}`);
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
  await aceptarConsentimiento(p);
  ok("cuenta verificada e inicio de sesión");

  console.log("Perfil y acceso a registros de salud");
  await p.fill('form[data-testid="form-crear-perfil"] input[name=nombre]', "Carlos Ruiz");
  await p.fill('form[data-testid="form-crear-perfil"] input[name=fecha_nacimiento]', "1970-05-20");
  await p.click('form[data-testid="form-crear-perfil"] button[type=submit]');
  await p.getByText('Perfil "Carlos Ruiz" creado').waitFor();
  await p.getByRole("link", { name: "Carlos Ruiz" }).click();
  await p.getByTestId("titulo-perfil").waitFor();
  const idPerfil = p.url().split("/perfiles/")[1];
  ok("perfil creado y abierto");

  await p.getByTestId("enlace-medicacion").click();
  await p.getByTestId("titulo-salud").getByText("Medicación").waitFor();
  ok("el enlace lleva a Medicación");

  console.log("Pauta con horas fijas y tomas de hoy");
  await p.fill('form[data-testid="form-medicamento"] input[name=nombre]', "Losartán");
  await p.fill('form[data-testid="form-medicamento"] input[name=dosis]', "50 mg");
  await p.fill('form[data-testid="form-medicamento"] input[name=horas]', "08:00, 20:00");
  await p.click('form[data-testid="form-medicamento"] button[type=submit]');
  await p.getByText("Pauta creada").waitFor();
  await p.getByTestId("lista-medicamentos").getByText("Losartán").waitFor();
  ok("la pauta aparece en la lista");

  const tomas = p.getByTestId("tomas-hoy").getByTestId("toma");
  await tomas.nth(0).waitFor();
  const horas = await tomas.evaluateAll((els) => els.map((e) => e.getAttribute("data-hora")));
  if (horas.join(",") !== "08:00,20:00") throw new Error(`Horas de tomas inesperadas: ${horas.join(",")}`);
  ok("las tomas de hoy se muestran a las 08:00 y 20:00 (hora de Bogotá)");

  const primera = tomas.nth(0);
  await primera.getByRole("button", { name: "Tomada" }).click();
  await p.getByText("Toma marcada como tomada").waitFor();
  await primera.getByTestId("estado-toma").getByText("Tomada").waitFor();
  ok("registrar una toma cambia su estado");

  await primera.getByRole("button", { name: "Omitida" }).click();
  await p.getByText("Toma marcada como omitida").waitFor();
  await primera.getByTestId("estado-toma").getByText("Omitida").waitFor();
  await p.reload();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).getByTestId("estado-toma").getByText("Omitida").waitFor();
  ok("una corrección gana tras recargar la página");

  await p.getByRole("button", { name: "Desactivar" }).click();
  await p.getByText("Pauta desactivada").waitFor();
  await p.getByTestId("lista-medicamentos").getByText("inactiva").waitFor();
  await p.getByText("No hay tomas programadas para hoy.").waitFor();
  ok("desactivar la pauta quita sus tomas de hoy");
  await p.getByRole("button", { name: "Reactivar" }).click();
  await p.getByText("Pauta reactivada").waitFor();
  await p.getByTestId("tomas-hoy").getByTestId("toma").nth(0).waitFor();
  ok("reactivar la pauta devuelve las tomas");

  await p.screenshot({ path: path.join(SHOTS, "medicacion.png"), fullPage: true });

  console.log("Síntomas");
  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Síntomas" }).click();
  await p.getByTestId("titulo-salud").getByText("Síntomas").waitFor();
  await p.fill('form[data-testid="form-sintoma"] input[name=sintoma]', "Dolor de cabeza");
  await p.fill('form[data-testid="form-sintoma"] input[name=intensidad]', "7");
  await p.fill('form[data-testid="form-sintoma"] textarea[name=nota]', "Después del almuerzo");
  await p.click('form[data-testid="form-sintoma"] button[type=submit]');
  await p.getByText("Síntoma registrado").waitFor();
  const sintoma = p.getByTestId("lista-sintomas").getByTestId("sintoma");
  await sintoma.getByText("Dolor de cabeza").waitFor();
  await sintoma.getByText("intensidad 7/10").waitFor();
  await p.getByTestId("lista-sintomas").getByText(/Después del almuerzo/).waitFor();
  ok("síntoma guardado con intensidad y nota");

  // El campo numérico tiene máximo 10: el navegador lo marca como inválido antes de enviar.
  await p.fill('form[data-testid="form-sintoma"] input[name=intensidad]', "11");
  const valida = await p.locator('form[data-testid="form-sintoma"] input[name=intensidad]').evaluate((el) => el.checkValidity());
  if (valida) throw new Error("La intensidad 11 debería marcarse como inválida");
  await p.fill('form[data-testid="form-sintoma"] input[name=intensidad]', "5");
  ok("una intensidad fuera de rango se marca como inválida antes de enviar");

  console.log("Diagnósticos");
  await p.getByRole("navigation", { name: "Registros de salud" }).getByRole("link", { name: "Diagnósticos" }).click();
  await p.getByTestId("titulo-salud").getByText("Diagnósticos").waitFor();
  await p.fill('form[data-testid="form-diagnostico"] textarea[name=descripcion]', "Hipertensión arterial");
  await p.click('form[data-testid="form-diagnostico"] button[type=submit]');
  await p.getByText("Diagnóstico registrado").waitFor();
  const diagnostico = p.getByTestId("lista-diagnosticos").getByTestId("diagnostico");
  await diagnostico.getByText("Hipertensión arterial").waitFor();
  await diagnostico.getByTestId("estado-diagnostico").getByText("Vigente").waitFor();
  ok("diagnóstico vigente registrado");

  await diagnostico.getByRole("button", { name: "Marcar resuelto" }).click();
  await p.getByText("Diagnóstico marcado como resuelto").waitFor();
  await diagnostico.getByTestId("estado-diagnostico").getByText("Resuelto").waitFor();
  await p.getByLabel("Mostrar resueltos").uncheck();
  await p.getByText("No hay diagnósticos para mostrar.").waitFor();
  ok("resolver y ocultar resueltos funcionan");
  await p.screenshot({ path: path.join(SHOTS, "diagnosticos.png"), fullPage: true });

  // Verificación de accesos: la página de medicación de un perfil ajeno no muestra datos.
  await p.goto(`${BASE}/perfiles/00000000-0000-4000-8000-000000000000/medicacion`);
  await p.getByRole("alert").waitFor();
  ok("un perfil inexistente o sin acceso no muestra registros");

  await p.goto(`${BASE}/perfiles/${idPerfil}/medicacion`);
  await p.getByTestId("tomas-hoy").waitFor();
  ok("volver a la ruta del perfil carga sus tomas");

  // Diseño móvil: la página no debe desplazarse horizontalmente a 375 px de ancho.
  await p.setViewportSize({ width: 375, height: 800 });
  await p.goto(`${BASE}/perfiles/${idPerfil}/diagnosticos`);
  await p.getByTestId("titulo-salud").waitFor();
  const desborde = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (desborde > 0) throw new Error(`Desplazamiento horizontal de ${desborde}px a 375px`);
  await p.screenshot({ path: path.join(SHOTS, "diagnosticos-movil.png"), fullPage: true });
  ok("sin desplazamiento horizontal a 375 px");
} catch (e) {
  errores.push(`flujo: ${e.message}`);
  await p.screenshot({ path: path.join(SHOTS, "fallo-salud.png"), fullPage: true }).catch(() => {});
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
