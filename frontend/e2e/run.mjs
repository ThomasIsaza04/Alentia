// Prueba de extremo a extremo: recorre la aplicación en un navegador real con dos cuentas.
// Requiere backend en 127.0.0.1:8000 (log en BACKEND_LOG) y Vite en 127.0.0.1:5173.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const LOG = process.env.BACKEND_LOG;
const CHROME = process.env.CHROME_PATH;
const SHOTS = process.env.SHOTS_DIR || "./shots";
const CLAVE = "Clave-segura-2026";
const sufijo = Date.now().toString(36);
const correoA = `ana.${sufijo}@ejemplo.co`;
const correoB = `luis.${sufijo}@ejemplo.co`;
const errores = [];
const pasos = [];

fs.mkdirSync(SHOTS, { recursive: true });
const ok = (msg) => { pasos.push(msg); console.log(`  ✔ ${msg}`); };

async function esperarEnlace(correo, tipo) {
  // El correo de desarrollo se imprime en el log del backend; se toma el último enlace de ese tipo.
  const marca = tipo === "verificar" ? "verificar?token=" : "aceptar-invitacion?token=";
  for (let i = 0; i < 40; i++) {
    const lineas = fs.readFileSync(LOG, "utf8").split("\n")
      .filter((l) => l.includes(`para ${correo}:`) && l.includes(marca));
    if (lineas.length) return lineas.at(-1).match(/token=([A-Za-z0-9_-]+)/)[1];
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`No apareció el enlace de ${tipo} para ${correo}`);
}

async function llamarApi(contexto, metodo, ruta, cuerpo) {
  const r = await contexto.request.fetch(`${BASE}${ruta}`, {
    method: metodo, data: cuerpo, headers: { "Content-Type": "application/json" },
  });
  if (!r.ok()) throw new Error(`${metodo} ${ruta} -> ${r.status()} ${await r.text()}`);
  return r.json();
}

function vigilar(pagina, nombre) {
  pagina.on("pageerror", (e) => errores.push(`[${nombre}] pageerror: ${e.message}`));
  pagina.on("console", (m) => {
    // El navegador registra cada respuesta HTTP de error como "Failed to load resource".
    // Esas respuestas (401 al iniciar sin sesión, 404 tras revocar) son esperadas y se comprueban en la prueba.
    if (m.type() === "error" && !m.text().includes("Failed to load resource")) {
      errores.push(`[${nombre}] console: ${m.text()}`);
    }
  });
}

const navegador = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const ctxA = await navegador.newContext({ viewport: { width: 1000, height: 800 }, locale: "es-CO" });
const ctxB = await navegador.newContext({ viewport: { width: 1000, height: 800 }, locale: "es-CO" });
const a = await ctxA.newPage();
const b = await ctxB.newPage();
a.setDefaultTimeout(8000);
b.setDefaultTimeout(8000);
vigilar(a, "A");
vigilar(b, "B");

try {
  console.log("Cuenta A: registro, verificación, inicio de sesión");
  await a.goto(`${BASE}/registro`);
  await a.fill("input[name=correo]", correoA);
  await a.fill("input[name=clave]", CLAVE);
  await a.click("button[type=submit]");
  await a.getByText("Si los datos son válidos").waitFor();
  ok("registro muestra el mensaje genérico de verificación");

  const tokenA = await esperarEnlace(correoA, "verificar");
  await a.goto(`${BASE}/verificar?token=${tokenA}`);
  await a.getByText("Correo verificado").waitFor();
  ok("el enlace de verificación confirma el correo");

  await a.goto(`${BASE}/login`);
  await a.fill("input[name=correo]", correoA);
  await a.fill("input[name=clave]", CLAVE);
  await a.click("button[type=submit]");
  await a.getByRole("heading", { name: "Mis perfiles" }).waitFor();
  ok("inicio de sesión lleva a Mis perfiles");

  console.log("Cuenta A: perfiles y zonas");
  await a.fill('form[data-testid="form-crear-perfil"] input[name=nombre]', "María Pérez");
  await a.fill('form[data-testid="form-crear-perfil"] input[name=fecha_nacimiento]', "1980-01-01");
  await a.click('form[data-testid="form-crear-perfil"] button[type=submit]');
  await a.getByText('Perfil "María Pérez" creado').waitFor();
  ok("crear perfil muestra confirmación");

  await a.getByRole("link", { name: "María Pérez" }).click();
  await a.getByTestId("titulo-perfil").waitFor();
  const urlPerfil = a.url();
  const idPerfil = urlPerfil.split("/perfiles/")[1];
  ok("el detalle del perfil abre con su nombre");

  await a.fill('form[data-testid="form-zona"] input[name=nombre]', "Cardiología");
  await a.click('form[data-testid="form-zona"] button[type=submit]');
  await a.getByTestId("lista-zonas").getByText("Cardiología").waitFor();
  ok("agregar zona la muestra en la lista");

  const liZona = a.getByTestId("lista-zonas").locator("li", { hasText: "Cardiología" });
  await liZona.getByRole("button", { name: "Archivar" }).click();
  await a.getByText("Zona archivada").waitFor();
  await a.getByTestId("lista-zonas").getByText("Cardiología").waitFor({ state: "detached" });
  ok("archivar oculta la zona por defecto");
  await a.getByLabel("Mostrar archivadas").check();
  await a.getByTestId("lista-zonas").getByText("Cardiología").waitFor();
  ok("con 'Mostrar archivadas' la zona vuelve a verse, marcada como archivada");
  await a.screenshot({ path: path.join(SHOTS, "a-detalle-perfil.png"), fullPage: true });

  await a.fill('form[data-testid="form-editar-perfil"] input[name=nombre]', "María P.");
  await a.click('form[data-testid="form-editar-perfil"] button[type=submit]');
  await a.getByText("Perfil actualizado").waitFor();
  await a.getByTestId("titulo-perfil").getByText("María P.").waitFor();
  ok("editar el nombre se refleja en el título");

  console.log("Invitación a la cuenta B");
  await llamarApi(ctxB, "POST", "/api/v1/auth/register", { correo: correoB, clave: CLAVE });
  const tokenVerB = await esperarEnlace(correoB, "verificar");
  await llamarApi(ctxB, "POST", "/api/v1/auth/verify-email", { token: tokenVerB });
  ok("la cuenta B queda verificada");

  await a.fill('form[data-testid="form-invitar"] input[name=correo]', correoB);
  await a.selectOption('form[data-testid="form-invitar"] select[name=alcance]', "lector");
  await a.click('form[data-testid="form-invitar"] button[type=submit]');
  await a.getByText("Si el correo es válido, se envió la invitación").waitFor();
  ok("invitar muestra la confirmación");
  const tokenInvB = await esperarEnlace(correoB, "aceptar");

  console.log("Cuenta B: invitación con redirección a inicio de sesión");
  await b.goto(`${BASE}/aceptar-invitacion?token=${tokenInvB}`);
  await b.getByRole("main").getByRole("link", { name: "Iniciar sesión" }).click();
  await b.fill("input[name=correo]", correoB);
  await b.fill("input[name=clave]", "clave-incorrecta-2026");
  await b.click("button[type=submit]");
  await b.getByRole("alert").getByText("Correo o contraseña incorrectos").waitFor();
  ok("contraseña incorrecta muestra el mensaje genérico");

  await b.fill("input[name=clave]", CLAVE);
  await b.click("button[type=submit]");
  await b.getByText("Invitación aceptada").waitFor();
  ok("tras iniciar sesión vuelve a la invitación y se acepta");

  await b.goto(`${BASE}/`);
  await b.getByRole("link", { name: "María P." }).waitFor();
  ok("el perfil aparece en la lista de B con alcance Lector");
  await b.getByRole("link", { name: "María P." }).click();
  await b.getByTestId("titulo-perfil").waitFor();
  const formularios = await b.locator('form[data-testid="form-editar-perfil"], form[data-testid="form-zona"], form[data-testid="form-invitar"]').count();
  if (formularios !== 0) throw new Error("Un lector ve formularios de edición");
  ok("el lector no ve formularios de edición, zonas ni invitaciones");
  await b.screenshot({ path: path.join(SHOTS, "b-lector.png"), fullPage: true });

  console.log("Revocación");
  await a.goto(`${BASE}${urlPerfil.replace(BASE, "")}`);
  const filaB = a.getByTestId("lista-accesos").locator("li", { hasText: correoB });
  await filaB.getByRole("button", { name: "Revocar" }).click();
  await a.getByText("Acceso revocado").waitFor();
  ok("el titular revoca el acceso de B");

  await b.goto(`${BASE}/perfiles/${idPerfil}`);
  await b.getByText("Perfil no encontrado").waitFor();
  ok("B ya no puede abrir el perfil (404 mostrado como 'no encontrado')");

  console.log("Errores de consola");
  if (errores.length) throw new Error(`Errores en el navegador:\n${errores.join("\n")}`);
  ok("sin errores de JavaScript ni de consola");

  console.log(`\nResultado: ${pasos.length} comprobaciones correctas.`);
} catch (e) {
  await a.screenshot({ path: path.join(SHOTS, "fallo-a.png"), fullPage: true }).catch(() => {});
  await b.screenshot({ path: path.join(SHOTS, "fallo-b.png"), fullPage: true }).catch(() => {});
  console.error(`\n✘ ${e.message}`);
  console.error(`Comprobaciones correctas antes del fallo: ${pasos.length}`);
  process.exitCode = 1;
} finally {
  await navegador.close();
}
