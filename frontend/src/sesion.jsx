import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ErrorApi, fijarToken, renovarSesion } from "./api.js";
import { borrarCacheDatos } from "./offline/outbox.js";

const ContextoSesion = createContext(null);

// Último usuario conocido (solo id, correo y verificación). Permite abrir la app sin red.
// No guarda tokens: sin red no hay datos nuevos, solo lo que está en caché.
const CLAVE_USUARIO = "alentia.ultimoUsuario";
const INTERVALO_REINTENTO_MS = 30000;

function guardarUsuario(usuario) {
  try {
    localStorage.setItem(
      CLAVE_USUARIO,
      JSON.stringify({ id: usuario.id, correo: usuario.correo, verificado: usuario.verificado })
    );
  } catch {
    // Almacenamiento bloqueado: la app funciona igual, solo no abre sin red.
  }
}

function leerUsuarioGuardado() {
  try {
    const valor = localStorage.getItem(CLAVE_USUARIO);
    return valor ? JSON.parse(valor) : null;
  } catch {
    return null;
  }
}

function borrarUsuarioGuardado() {
  try {
    localStorage.removeItem(CLAVE_USUARIO);
  } catch {
    // Nada que borrar.
  }
}

export function SesionProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargarUsuario = useCallback(async () => {
    const datos = await api("/api/v1/auth/me");
    guardarUsuario(datos);
    setUsuario(datos);
    return datos;
  }, []);

  // Restaura la sesión con la cookie. Sin red, mantiene el último usuario conocido en modo sin conexión.
  const restaurar = useCallback(async () => {
    try {
      await renovarSesion();
      await cargarUsuario();
    } catch (error) {
      const guardado = leerUsuarioGuardado();
      if (!(error instanceof ErrorApi) && guardado) {
        setUsuario({ ...guardado, sinConexion: true });
        return;
      }
      fijarToken(null);
      borrarUsuarioGuardado();
      setUsuario(null);
    }
  }, [cargarUsuario]);

  useEffect(() => {
    // Al abrir la aplicación, si hay una cookie de sesión válida, la sesión se restaura sola.
    restaurar().finally(() => setCargando(false));
  }, [restaurar]);

  // Con sesión sin conexión, se vuelve a comprobar al recuperar la red y periódicamente.
  const sinConexion = Boolean(usuario?.sinConexion);
  useEffect(() => {
    if (!sinConexion) return undefined;
    const reintentar = () => {
      if (navigator.onLine) restaurar();
    };
    const temporizador = setInterval(reintentar, INTERVALO_REINTENTO_MS);
    window.addEventListener("online", reintentar);
    return () => {
      clearInterval(temporizador);
      window.removeEventListener("online", reintentar);
    };
  }, [sinConexion, restaurar]);

  const iniciarSesion = async (correo, clave) => {
    const datos = await api("/api/v1/auth/login", {
      metodo: "POST",
      cuerpo: { correo, clave },
      sinSesion: true,
    });
    fijarToken(datos.access_token);
    return cargarUsuario();
  };

  const cerrarSesion = async () => {
    try {
      await api("/api/v1/auth/logout", { metodo: "POST", sinSesion: true });
    } finally {
      fijarToken(null);
      borrarUsuarioGuardado();
      await borrarCacheDatos();
      setUsuario(null);
    }
  };

  return (
    <ContextoSesion.Provider
      value={{ usuario, cargando, sinConexion, iniciarSesion, cerrarSesion, recargar: cargarUsuario }}
    >
      {children}
    </ContextoSesion.Provider>
  );
}

export function useSesion() {
  return useContext(ContextoSesion);
}
