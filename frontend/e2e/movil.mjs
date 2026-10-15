// Comprueba que las pantallas principales no tienen desplazamiento horizontal en un teléfono (375 px).
import { chromium } from "playwright-core";
import fs from "node:fs";
const BASE = "http://127.0.0.1:5173";
const navegador = await chromium.launch({ executablePath: process.env.CHROME_PATH, args: ["--no-sandbox"] });
const pagina = await navegador.newPage({ viewport: { width: 375, height: 800 }, locale: "es-CO" });
const salida = [];
for (const ruta of ["/login", "/registro", "/recuperar"]) {
  await pagina.goto(BASE + ruta);
  await pagina.waitForSelector("h1");
  const desbordado = await pagina.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  salida.push(`${ruta}: ${desbordado ? "DESBORDA" : "ok"}`);
  if (ruta === "/login") await pagina.screenshot({ path: process.env.SHOTS_DIR + "/movil-login.png", fullPage: true });
}
console.log(salida.join("\n"));
await navegador.close();
