import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ErrorApi } from "../api.js";
import { Mensaje } from "../componentes.jsx";
import { useSesion } from "../sesion.jsx";

function siguienteSeguro(valor) {
  // Solo rutas internas de la aplicación, para evitar redirecciones a otros sitios.
  return valor && valor.startsWith("/") && !valor.startsWith("//") ? valor : "/";
}

export function Login() {
  const { iniciarSesion } = useSesion();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    setError("");
    setEnviando(true);
    try {
      await iniciarSesion(datos.get("correo"), datos.get("clave"));
      navegar(siguienteSeguro(params.get("siguiente")), { replace: true });
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="tarjeta">
      <h1>Iniciar sesión</h1>
      <form onSubmit={enviar} className="formulario">
        <label>Correo<input name="correo" type="email" required autoComplete="email" /></label>
        <label>Contraseña<input name="clave" type="password" required autoComplete="current-password" /></label>
        <Mensaje>{error}</Mensaje>
        <button type="submit" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
      </form>
      <p className="enlaces">
        <Link to="/registro">Crear cuenta</Link> · <Link to="/recuperar">Olvidé mi contraseña</Link>
      </p>
    </section>
  );
}

export function Registro() {
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  async function enviar(evento) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    setError("");
    try {
      const r = await api("/api/v1/auth/register", {
        metodo: "POST",
        cuerpo: { correo: datos.get("correo"), clave: datos.get("clave") },
        sinSesion: true,
      });
      setMensaje(r.mensaje);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="tarjeta">
      <h1>Crear cuenta</h1>
      <form onSubmit={enviar} className="formulario">
        <label>Correo<input name="correo" type="email" required /></label>
        <label>Contraseña (mínimo 10 caracteres)<input name="clave" type="password" required minLength={10} /></label>
        <Mensaje>{error}</Mensaje>
        <Mensaje tipo="ok">{mensaje}</Mensaje>
        <button type="submit">Registrarme</button>
      </form>
      <p className="enlaces"><Link to="/login">Ya tengo cuenta</Link></p>
    </section>
  );
}

export function Verificar() {
  const [params] = useSearchParams();
  const [resultado, setResultado] = useState({ tipo: "", texto: "Verificando…" });
  const enviado = useRef(false);

  useEffect(() => {
    // El token es de un solo uso: se envía una sola vez aunque React repita el efecto.
    if (enviado.current) return;
    enviado.current = true;
    const token = params.get("token");
    if (!token) {
      setResultado({ tipo: "error", texto: "El enlace no tiene un token válido" });
      return;
    }
    api("/api/v1/auth/verify-email", { metodo: "POST", cuerpo: { token }, sinSesion: true })
      .then((r) => setResultado({ tipo: "ok", texto: r.mensaje }))
      .catch((e) => setResultado({ tipo: "error", texto: e.message }));
  }, [params]);

  return (
    <section className="tarjeta">
      <h1>Verificar correo</h1>
      <Mensaje tipo={resultado.tipo || "ok"}>{resultado.texto}</Mensaje>
      <p className="enlaces"><Link to="/login">Ir a iniciar sesión</Link></p>
    </section>
  );
}

export function Recuperar() {
  const [mensaje, setMensaje] = useState("");
  async function enviar(evento) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    const r = await api("/api/v1/auth/forgot-password", {
      metodo: "POST",
      cuerpo: { correo: datos.get("correo") },
      sinSesion: true,
    });
    setMensaje(r.mensaje);
  }
  return (
    <section className="tarjeta">
      <h1>Recuperar contraseña</h1>
      <form onSubmit={enviar} className="formulario">
        <label>Correo<input name="correo" type="email" required /></label>
        <Mensaje tipo="ok">{mensaje}</Mensaje>
        <button type="submit">Enviar instrucciones</button>
      </form>
    </section>
  );
}

export function Restablecer() {
  const [params] = useSearchParams();
  const [resultado, setResultado] = useState({ tipo: "", texto: "" });
  async function enviar(evento) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    try {
      const r = await api("/api/v1/auth/reset-password", {
        metodo: "POST",
        cuerpo: { token: params.get("token") || "", clave: datos.get("clave") },
        sinSesion: true,
      });
      setResultado({ tipo: "ok", texto: r.mensaje });
    } catch (e) {
      setResultado({ tipo: "error", texto: e instanceof ErrorApi ? e.message : "Error" });
    }
  }
  return (
    <section className="tarjeta">
      <h1>Nueva contraseña</h1>
      <form onSubmit={enviar} className="formulario">
        <label>Nueva contraseña<input name="clave" type="password" required minLength={10} /></label>
        <Mensaje tipo={resultado.tipo || "ok"}>{resultado.texto}</Mensaje>
        <button type="submit">Guardar</button>
      </form>
    </section>
  );
}

export function AceptarInvitacion() {
  const [params] = useSearchParams();
  const { usuario } = useSesion();
  const [resultado, setResultado] = useState({ tipo: "", texto: "" });
  const enviado = useRef(false);

  useEffect(() => {
    if (!usuario || enviado.current) return;
    enviado.current = true;
    api("/api/v1/invitaciones/aceptar", { metodo: "POST", cuerpo: { token: params.get("token") || "" } })
      .then((r) => setResultado({ tipo: "ok", texto: `${r.mensaje}. Ya puedes ver el perfil en tu lista.` }))
      .catch((e) => setResultado({ tipo: "error", texto: e.message }));
  }, [usuario, params]);

  if (!usuario) {
    const siguiente = encodeURIComponent(`/aceptar-invitacion?token=${params.get("token") || ""}`);
    return (
      <section className="tarjeta">
        <h1>Aceptar invitación</h1>
        <p>Inicia sesión con el correo al que llegó la invitación para aceptarla.</p>
        <Link to={`/login?siguiente=${siguiente}`}>Iniciar sesión</Link>
      </section>
    );
  }
  return (
    <section className="tarjeta">
      <h1>Aceptar invitación</h1>
      <Mensaje tipo={resultado.tipo || "ok"}>{resultado.texto || "Aceptando…"}</Mensaje>
      <p className="enlaces"><Link to="/">Ir a mis perfiles</Link></p>
    </section>
  );
}
