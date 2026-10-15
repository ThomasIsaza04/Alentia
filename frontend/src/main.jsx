import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { SesionProvider } from "./sesion.jsx";

// El service worker solo se registra en producción (vista previa o build). En desarrollo, Vite recarga sin caché.
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Sin service worker la app sigue funcionando en línea.
    });
  });
}

createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <SesionProvider>
      <App />
    </SesionProvider>
  </BrowserRouter>
);
