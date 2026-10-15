import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useSesion } from "./sesion.jsx";

export function Mensaje({ tipo = "error", children }) {
  if (!children) return null;
  return (
    <p className={`mensaje ${tipo}`} role={tipo === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

export function RutaPrivada({ children }) {
  const { usuario, cargando } = useSesion();
  const ubicacion = useLocation();
  if (cargando) return <p className="cargando">Cargando…</p>;
  if (!usuario) {
    const siguiente = encodeURIComponent(ubicacion.pathname + ubicacion.search);
    return <Navigate to={`/login?siguiente=${siguiente}`} replace />;
  }
  return children;
}

export function formatearFecha(valor) {
  if (!valor) return "";
  const [anio, mes, dia] = String(valor).slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

export const ETIQUETAS_ALCANCE = { lector: "Lector", editor: "Editor", admin: "Administrador" };
export const ETIQUETAS_ROL = { titular: "Titular", representante: "Representante", cuidador: "Cuidador" };
