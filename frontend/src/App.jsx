import React from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import { RutaPrivada } from "./componentes.jsx";
import { AceptarInvitacion, Login, Recuperar, Registro, Restablecer, Verificar } from "./paginas/Cuenta.jsx";
import Perfiles from "./paginas/Perfiles.jsx";
import PerfilDetalle from "./paginas/PerfilDetalle.jsx";
import { Diagnosticos, Medicacion, Sintomas } from "./paginas/Salud.jsx";
import AccesoTemporal from "./paginas/AccesoTemporal.jsx";
import AccesoProfesional from "./paginas/AccesoProfesional.jsx";
import MiCuenta from "./paginas/MiCuenta.jsx";
import Recordatorios from "./paginas/Recordatorios.jsx";
import { EstadoConexion } from "./conexion.jsx";
import { useSesion } from "./sesion.jsx";

function Cabecera() {
  const { usuario, cerrarSesion } = useSesion();
  const navegar = useNavigate();
  return (
    <header className="cabecera">
      <Link to="/" className="marca">Alentia</Link>
      {usuario ? (
        <nav>
          <span className="correo">{usuario.correo}</span>
          <Link to="/cuenta">Mi cuenta</Link>
          <button
            className="secundario"
            onClick={async () => {
              await cerrarSesion();
              navegar("/login", { replace: true });
            }}
          >
            Salir
          </button>
        </nav>
      ) : (
        <nav><Link to="/login">Iniciar sesión</Link></nav>
      )}
    </header>
  );
}

export default function App() {
  return (
    <>
      <Cabecera />
      <main className="contenido">
        <EstadoConexion />
        <Recordatorios />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/verificar" element={<Verificar />} />
          <Route path="/recuperar" element={<Recuperar />} />
          <Route path="/restablecer" element={<Restablecer />} />
          <Route path="/aceptar-invitacion" element={<AceptarInvitacion />} />
          <Route path="/" element={<RutaPrivada><Perfiles /></RutaPrivada>} />
          <Route path="/perfiles/:id" element={<RutaPrivada><PerfilDetalle /></RutaPrivada>} />
          <Route path="/perfiles/:id/medicacion" element={<RutaPrivada><Medicacion /></RutaPrivada>} />
          <Route path="/perfiles/:id/sintomas" element={<RutaPrivada><Sintomas /></RutaPrivada>} />
          <Route path="/perfiles/:id/acceso" element={<RutaPrivada><AccesoTemporal /></RutaPrivada>} />
          <Route path="/acceso/:token" element={<AccesoProfesional />} />
          <Route path="/cuenta" element={<RutaPrivada><MiCuenta /></RutaPrivada>} />
          <Route path="/perfiles/:id/diagnosticos" element={<RutaPrivada><Diagnosticos /></RutaPrivada>} />
          <Route path="*" element={<section className="tarjeta"><h1>Página no encontrada</h1></section>} />
        </Routes>
      </main>
    </>
  );
}
