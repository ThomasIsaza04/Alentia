# Alentia — Bóveda de salud personal y familiar (PWA)

Proyecto de grado · Tecnólogo en ADSO · SENA. Documento maestro v0.1 en `docs/`.

> Alentia no es una historia clínica ni reemplaza la indicación médica.

## Requisitos

- Python 3.12 (recomendado; coincide con la imagen Docker).
- Docker Desktop para levantar PostgreSQL.

## Instalación (backend)

1. Levantar la base de datos: `docker compose up -d db` (desde la carpeta `alentia`).
2. Entrar a `backend`, crear el entorno virtual con Python 3.12 y activarlo.
3. Instalar dependencias: `pip install -r requirements.txt`.
4. Copiar `.env.example` a `.env` y generar la llave de cifrado (ver comentario en el archivo).
5. Aplicar migraciones: `alembic upgrade head`.
6. Ejecutar la API: `uvicorn app.main:app --reload` y abrir http://localhost:8000/docs.

## Pruebas

- `pytest` ejecuta todas las pruebas. Las de base de datos requieren `TEST_DATABASE_URL` en `.env`.
- `ruff check .` verifica el estilo.

## Estado

- Paso 1 (completado): esqueleto del backend, `/health`, cabeceras de seguridad, pruebas, Docker.
- Paso 2 (completado): PostgreSQL 16, modelos base, migraciones 0001 y 0002 con Alembic, cifrado AES-256-GCM con rotación de llaves, tablas de solo adición.
- Paso 3 (completado con correcciones de revisión): registro, verificación de correo, inicio de sesión con Argon2id, tokens de acceso de 15 minutos, refresh rotativo con detección de reutilización, bloqueo tras 5 intentos sin revelar si la cuenta existe, recuperación de contraseña, política de seguridad de contenido por ruta y rol de aplicación con permisos mínimos (migración 0003).
- Paso 4 (completado): perfiles propios y dependientes, zonas de consulta cifradas, invitaciones con token de un solo uso y vencimiento de 72 horas, revocación de accesos y reglas de menor con representante. Migración 0004. Detalle y diferencias con la especificación en la sección 9.6 de `docs/ALENTIA_documento_maestro.md`.
- Pendiente en el paso 3: límite de peticiones con slowapi (login y QR) y envío real de correo con Brevo.
- Interfaz web (frontend en React): autenticación, perfiles, zonas e invitaciones (18 comprobaciones en navegador real), más medicación, síntomas y diagnósticos (16 comprobaciones, incluida la vista móvil a 375 px).
- Paso 5 (completado): medicación con pautas de horas fijas o cada N horas, tomas programadas 30 días hacia adelante (guardadas en UTC y mostradas en la zona horaria del cliente), registro de tomas tomada/omitida/pospuesta con idempotencia por identificador de cliente, y corrección por registro nuevo (gana el más reciente).
- Paso 6 (completado): síntomas con intensidad 0–10 y nota cifrada, y diagnósticos con zona de consulta opcional y estado vigente/resuelto.
- Paso 7 (completado): acceso temporal para profesionales con código QR y PIN de seis dígitos, duración de 15 o 30 minutos, bloqueo tras cinco PIN incorrectos, revocación inmediata y bitácora. Token y PIN se guardan como hash. Migración 0005. Detalle en la sección 9.8 de `docs/ALENTIA_documento_maestro.md`.
- Paso 8 (completado): consentimiento por finalidad (salud, notificaciones, qr) con versión de política, exportación en JSON y CSV, eliminación con siete días de gracia y correcciones por registro nuevo. Migración 0006. Detalle en la sección 9.9.
- Paso 9 (completado): recordatorios dentro de la aplicación, estados de atraso y omisión automática, extensión de tomas y calendario `.ics`. Migración 0007 (zona horaria por pauta). Detalle en la sección 9.10. Push (RF-NOT-01) y alertas a tutores (RF-NOT-04) no están implementados.
- PWA (completado): manifiesto e iconos, service worker generado en el build, lecturas sin conexión, cola local de tomas y síntomas con reenvío idempotente, indicador de pendientes y rechazados. Detalle en la sección 9.11.
- ADM: `GET /health` cumple RF-ADM-01; las métricas (RF-ADM-02) no están implementadas.
- Tareas programadas: `python -m app.tareas.ejecutar` (omisiones y extensiones) y `python -m app.tareas.purgar_cuentas` (eliminación de cuentas vencidas). En producción deben ejecutarse con el programador del entorno de despliegue.

## Interfaz web (frontend)

Requisitos: Node.js 22 o superior.

1. Con el backend y la base de datos levantados (`docker compose up -d db api`), en `backend\.env` debe estar `COOKIE_SECURE=false` para desarrollo local.
2. En otra terminal, entrar a `frontend` e instalar: `npm install`.
3. Iniciar la interfaz: `npm run dev` y abrir http://localhost:5173.

Durante el desarrollo, Vite reenvía `/api` al backend en `localhost:8000`, así que no hace falta configurar CORS.

En desarrollo, el correo de verificación, de invitación y de recuperación no se envía: el enlace aparece en el log del backend (`docker compose logs api`). Copia el enlace en el navegador para continuar el flujo.

Pantallas disponibles: crear cuenta, verificar correo, iniciar sesión, recuperar y restablecer contraseña, mis perfiles, crear perfil, editar perfil, zonas de consulta (crear, archivar y restaurar), personas con acceso (invitar, revocar), aceptar invitación, medicación (pautas, tomas de hoy con Tomada/Omitida/Pospuesta, desactivar, descargar calendario), síntomas (registro y últimos 7 días), diagnósticos (registro, resolver y reabrir), acceso para profesional (QR, PIN, bitácora y revocación), la página del profesional (`/acceso/:token`), y «Mi cuenta» (consentimientos, exportación, eliminación con periodo de gracia). Los recordatorios de tomas aparecen en un banner sobre todas las pantallas.

**Modo sin conexión.** En producción (o en la vista previa) la aplicación se puede instalar y se registra un service worker. Para probarlo: `npm run build` y luego `node e2e/offline.mjs`; la prueba levanta la vista previa por sí misma en el puerto 4173.

Pruebas de navegador: las pruebas leen los enlaces de correo del log del backend, así que el backend debe escribir su salida a un archivo. Con el backend corriendo así (`uvicorn app.main:app --port 8000 > backend.log 2>&1`, desde `backend` y con el entorno activo), y con `BACKEND_LOG=../backend/backend.log CHROME_PATH=<ruta a Chromium>` definidas, se ejecuta cada suite con `node e2e/<nombre>.mjs` desde `frontend`:

- `run.mjs`: cuentas, perfiles e invitaciones (18 comprobaciones).
- `salud.mjs`: medicación, síntomas y diagnósticos, con vista móvil (16). Usa la zona horaria America/Bogota.
- `acceso.mjs`: acceso temporal para profesionales (8).
- `cuenta.mjs`: consentimientos, exportación y eliminación (9).
- `recordatorios.mjs`: banner y calendario `.ics` (5).
- `sesion.mjs`: renovación de sesión y recuperación de contraseña (7).
- `movil.mjs`: páginas públicas a 375 px.
- `offline.mjs`: modo sin conexión (13). Requiere `npm run build` antes; gestiona la vista previa en el puerto 4173.

## Base de datos y permisos

- La API se conecta con el rol `alentia_app` (`DATABASE_URL`). Ese rol no es dueño de las tablas y no puede modificar ni borrar `toma_registro`, `sintoma_registro` ni `auditoria`.
- Las migraciones usan `MIGRATION_DATABASE_URL` (rol dueño). Si no se define, usan `DATABASE_URL`, lo que solo es aceptable en desarrollo local.
- El script `db/init/01-rol-aplicacion.sh` crea el rol al inicializar la base de datos; requiere la variable `APP_DB_PASSWORD`.
- Para la prueba de permisos: `APP_TEST_DATABASE_URL` apunta a la base de pruebas con el rol de aplicación. Si no se define, esas pruebas se omiten.

## Verificación registrada

- `pytest`: 144 pruebas pasan sobre PostgreSQL 16, sin omisiones, al cierre del prototipado (13 de octubre de 2026). Para que las pruebas de base de datos se ejecuten, `TEST_DATABASE_URL` debe apuntar a una base cuyo nombre contenga `test`, y `APP_TEST_DATABASE_URL` al rol `alentia_app` sobre esa misma base.
- Pruebas e2e del navegador: 18 (cuentas), 16 (salud), 8 (acceso), 9 (cuenta), 5 (recordatorios), 7 (sesión), 13 (sin conexión) y `movil.mjs`, todas correctas.
- `ruff check .`: sin errores (ruff 0.6.9, la versión fijada en `requirements.txt`).
- Verificado en Windows con Docker Desktop: `docker compose` (base de datos y API), migraciones, `/docs` en navegador y flujo de registro, verificación e inicio de sesión.
- Pendiente: ejecutar las pruebas automatizadas dentro del contenedor.
