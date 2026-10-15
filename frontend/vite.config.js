import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { createHash } from "node:crypto";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const API = "http://127.0.0.1:8000";

// Genera dist/sw.js a partir de src/sw.js: la lista de archivos de la cáscara y una versión por contenido.
function servicioTrabajador() {
  return {
    name: "alentia-servicio-trabajador",
    apply: "build",
    generateBundle(_opciones, paquete) {
      const archivos = Object.keys(paquete)
        .filter((nombre) => !nombre.endsWith(".map"))
        .map((nombre) => `/${nombre}`);
      const cascara = ["/", ...archivos, "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];
      const version = createHash("sha256").update(cascara.join("\n")).digest("hex").slice(0, 12);
      const plantilla = fs.readFileSync(fileURLToPath(new URL("./src/sw.js", import.meta.url)), "utf8");
      this.emitFile({
        type: "asset",
        fileName: "sw.js",
        source: plantilla
          .replace('const VERSION = "__VERSION__"', `const VERSION = "${version}"`)
          .replace("const ARCHIVOS_SHELL = __ARCHIVOS__;", `const ARCHIVOS_SHELL = ${JSON.stringify([...new Set(cascara)])};`),
      });
    },
  };
}

// En desarrollo, el navegador habla con Vite (localhost:5173) y Vite reenvía /api al backend.
// Así las cookies de sesión son del mismo sitio y no hace falta configurar CORS para el navegador.
// La vista previa de producción (puerto 4173) se usa para probar el modo sin conexión.
export default defineConfig({
  plugins: [react(), servicioTrabajador()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": API },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    proxy: { "/api": API },
  },
});
