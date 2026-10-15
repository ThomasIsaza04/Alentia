# ALENTIA — Bóveda de salud personal y familiar (PWA)

**Documento maestro del proyecto de grado · Tecnólogo en Análisis y Desarrollo de Software (ADSO) · SENA**

| Campo | Valor |
|---|---|
| Versión | 0.3 (borrador para revisión del equipo) |
| Fecha | 13 de octubre de 2026 |
| Estado | En revisión. Nada de este documento está aprobado hasta que el equipo y el instructor lo validen |
| Nombre anterior | SORAKA P.G.S.C. |
| Ventana de entrega | 5 al 10 de diciembre de 2026 (confirmar fecha exacta con el instructor) |

> **Cómo usar este documento.** Está pensado para repasarse por secciones durante varios días. Las secciones 1 a 4 definen *qué* es el proyecto, las 5 a 8 definen *qué debe cumplir*, las 9 a 14 definen *cómo se construye y se opera*, y las 15 a 21 definen *cómo se gestiona, se defiende y se entrega*. Lo marcado con **[VERIFICAR]** es algo que no pude confirmar y que deben validar con su instructor, la guía de la ficha o un asesor legal. Lo marcado con **[DECIDIR]** es una decisión que le corresponde al equipo.

---

## Índice

1. Identidad del proyecto
2. Problema, justificación y objetivos
3. Alcance
4. Roles y matriz de permisos
5. Requisitos funcionales y criterios de aceptación
6. Requisitos no funcionales
7. Seguridad y privacidad por diseño
8. Marco normativo
9. Arquitectura y stack tecnológico
10. Modelo de datos preliminar
11. Contrato de API preliminar
12. Buenas prácticas de ingeniería
13. Estrategia de pruebas
14. Despliegue, operación y continuidad
15. Gestión del proyecto y cronograma
16. Matriz de riesgos
17. Entregables documentales y mapeo a la evaluación SENA
18. Plan de validación con usuarios
19. Plan de sustentación
20. Checklist pre-sustentación
21. Hoja de ruta (Fase 2) y decisiones pendientes

Anexos: A. Glosario · B. Plantilla de historia de usuario · C. Plantilla de ADR

---

## 1. Identidad del proyecto

### 1.1 Nombre

**Alentia** (propuesto). Viene de *aliento* y *alentar*: dar ánimo y energía para seguir un tratamiento. Es corto, se pronuncia igual en español e inglés y no menciona "clínico", lo que evita confundirlo con una historia clínica.

**Verificación realizada:** hice búsquedas web rápidas con "Alentia", "Kuyay", "Cuidara" y "Sanavia" y no encontré una aplicación de salud con exactamente esos nombres. Esto **no es una búsqueda de marca**. Antes de invertir en logo y dominio deben:

- consultar el buscador de marcas de la Superintendencia de Industria y Comercio (SIC) **[VERIFICAR]**;
- buscar el nombre en Google Play, App Store y en un registrador de dominios;
- buscar en redes sociales por si el usuario está tomado.

Descarté "Sanavia" y variantes de "Savia" porque **Savia** ya es una plataforma de salud digital conocida (de Mapfre).

**Alternativas si Alentia no pasa la verificación:** *Kuyay* (palabra quechua asociada a querer y cuidar; verificar el significado exacto antes de usarla), *Cuidara*, *Arca* (por "bóveda"). Cambiar el nombre después es un reemplazo de texto, así que no bloquea el avance. **[DECIDIR]**

**Lema provisional:** *"Tu salud, a tu cargo."*

### 1.2 Qué es

Una aplicación web progresiva (PWA) que funciona como **registro personal de salud (PHR)**: la persona, o quien la cuida, organiza en un solo lugar sus fórmulas, diagnósticos, exámenes, medicamentos y síntomas, recibe recordatorios, y puede mostrar un resumen a un profesional de salud durante una consulta mediante un acceso temporal y seguro, **sin que el profesional tenga que crear una cuenta**.

### 1.3 Qué NO es (descargo obligatorio, debe aparecer en la app y en los documentos)

- **No es una historia clínica** ni la reemplaza. Es un registro que gestiona el propio paciente y no tiene validez clínica por sí mismo.
- **No diagnostica, no receta y no recomienda tratamientos.**
- **No reemplaza la indicación médica**, ni sus recordatorios son alarmas garantizadas.
- **No se conecta con IPS, EPS ni sistemas clínicos** en esta entrega.

### 1.4 Estado del arte (para la sustentación)

Los jurados preguntarán "¿esto ya existe?". La respuesta honesta es que existen soluciones parecidas, y su diferencia debe ser clara:

| Solución | Qué hace | Limitación respecto a Alentia |
|---|---|---|
| Carpetas de salud de aseguradoras (por ejemplo la "Carpeta Personal de Salud" de Sanitas o "Mi Salud al Día" de DKV) | Repositorio de datos de salud del asegurado | Dependen de una aseguradora y su red; no son para cualquier persona |
| Savia (Mapfre) | Servicios de salud digitales, telemedicina | Es un servicio de atención, no un registro propio del paciente |
| TeCuido.cl (Chile) | Ordena medicamentos e historial de la familia, con asistente de IA | Es una plataforma de otro país y usa IA generativa; no está pensada para el contexto colombiano |
| Apps del Ministerio (por ejemplo ClicSalud) | Información pública del sistema de salud y quejas | No gestiona el registro personal del paciente |

**Diferenciadores propuestos de Alentia** (deben poder demostrarse):

1. Acceso del profesional **sin cuenta** mediante QR con PIN, un solo uso y bitácora visible para el paciente.
2. **Perfiles dependientes**: se puede gestionar la salud de un menor o de un adulto mayor sin que ellos tengan cuenta propia.
3. **Privacidad verificable**: el OCR corre en el dispositivo y la foto no sale de él; el resumen para el médico es determinista, sin IA generativa.
4. **Funciona sin conexión** para registrar tomas y síntomas.
5. Diseñada para el marco legal colombiano (Ley 1581 de 2012).

> Esta tabla se construyó con búsquedas web de alcance limitado. Antes de la sustentación, el equipo debe revisar directamente al menos 3 competidores y documentar sus hallazgos. **[VERIFICAR]**

---

## 2. Problema, justificación y objetivos

### 2.1 Planteamiento del problema

Las personas con tratamientos continuos, los cuidadores de menores y los de adultos mayores acumulan fórmulas en papel, resultados dispersos entre varias entidades y recuerdos imprecisos de síntomas. Esto produce consultas con información incompleta, olvido de tomas de medicamentos y dificultad para explicarle al profesional qué ha pasado desde la última cita.

> **Importante:** este párrafo es una hipótesis hasta que se valide. La sección 18 define cómo comprobarla con entrevistas. Si las entrevistas la contradicen, el problema se reformula.

### 2.2 Justificación

- **Técnica:** integra los componentes del programa ADSO: análisis, diseño, base de datos relacional, API REST, autenticación y autorización, frontend PWA, pruebas, contenedores, CI/CD y despliegue.
- **Social:** apoya la adherencia a tratamientos y el cuidado familiar sin exigir infraestructura clínica.
- **Normativa:** obliga a aplicar tratamiento responsable de datos sensibles, lo que demuestra criterio profesional.

### 2.3 Objetivo general

Desarrollar y desplegar una aplicación web progresiva que permita a personas y a sus cuidadores organizar su información de salud, recibir recordatorios de medicación y compartir un resumen con profesionales de forma temporal y segura, aplicando buenas prácticas de ingeniería de software y de protección de datos personales.

### 2.4 Objetivos específicos (cada uno medible)

| Id | Objetivo | Indicador de cumplimiento |
|---|---|---|
| OE1 | Levantar y documentar los requisitos con usuarios reales | Mínimo 5 entrevistas documentadas y requisitos priorizados |
| OE2 | Diseñar la arquitectura, el modelo de datos y los prototipos | Documentos de diseño aprobados por el instructor |
| OE3 | Implementar el núcleo funcional (bóveda, medicación, síntomas, tutores, QR) | 100 % de los requisitos "Debe" aceptados |
| OE4 | Implementar seguridad y cumplimiento de privacidad | Pruebas de seguridad del QR y de autorización aprobadas; consentimiento y derechos del titular operativos |
| OE5 | Garantizar calidad mediante pruebas automatizadas | Cobertura y criterios de la sección 13 |
| OE6 | Desplegar en un entorno accesible con CI/CD | Aplicación en línea y pipeline funcionando |
| OE7 | Validar con usuarios | Piloto con 5 a 10 personas y resultado SUS reportado |

### 2.5 Público objetivo

- **Primario:** adultos que gestionan su propio tratamiento continuo (hipertensión, diabetes, tratamientos de larga duración).
- **Primario:** madres, padres y representantes legales de menores; hijos o familiares que cuidan adultos mayores.
- **Secundario:** profesionales de salud, solo como receptores de un acceso temporal. No son usuarios registrados.

---

## 3. Alcance

### 3.1 Priorización MoSCoW

| Prioridad | Contenido |
|---|---|
| **Debe** | Registro, verificación de correo, inicio de sesión y recuperación de cuenta; perfiles de salud; zonas de consulta; diagnósticos, fórmulas y exámenes con archivos; medicamentos con horarios y registro de tomas; registro diario de síntomas; vínculos tutor-menor y adulto mayor-cuidador; consentimiento informado versionado; QR de acceso con PIN, vista de solo lectura y bitácora; PWA instalable con registro offline; exportar datos y eliminar cuenta |
| **Debería** | OCR local con confirmación obligatoria; notificaciones push; exportación de recordatorios a calendario (.ics); resumen determinista para el médico; PDF imprimible del resumen |
| **Podría** | Alertas por correo al tutor; inventario de medicamentos con aviso de reabastecimiento; modo oscuro; transición de menor a autonomía al cumplir 18; gráficos de adherencia |
| **No ahora** | IA generativa; integración con IPS/EPS/historia clínica; telemedicina; pagos; app nativa en tiendas |

### 3.2 Regla de congelación

- **Semana 7:** se congela el alcance. Lo que no esté en curso no se empieza.
- **Semana 9:** no se agregan funciones, solo se corrigen errores y se documenta.
- Cualquier cambio de alcance se registra en el tablero con quién lo aprobó y qué se quitó a cambio.

### 3.3 Supuestos

- Los usuarios tienen un teléfono o computador con navegador moderno y acceso a internet de forma intermitente.
- Se usará solo información sintética en desarrollo y en la demostración. En el piloto, las personas usarán datos reales solo si consienten expresamente, o datos ficticios que ellas inventen.
- Los servicios gratuitos mantienen sus condiciones hasta diciembre. **[VERIFICAR]** al inicio de la semana 1 y de nuevo en la semana 7.

### 3.4 Restricciones

- Cuatro integrantes, aproximadamente nueve semanas efectivas (con festivos incluidos).
- Presupuesto: costo cero de infraestructura donde sea posible.
- Stack decidido: Python (FastAPI), PostgreSQL, React.

---

## 4. Roles y matriz de permisos

### 4.1 Roles

| Rol | Descripción | ¿Tiene cuenta? |
|---|---|---|
| **Titular** | Adulto que gestiona su propio perfil de salud | Sí |
| **Representante legal** | Madre, padre o tutor legal de un menor de 18 años | Sí |
| **Cuidador delegado** | Persona a quien un adulto (por ejemplo un adulto mayor) delega permisos | Sí |
| **Profesional invitado** | Médico o especialista que recibe un QR en consulta | **No** |
| **Operador de plataforma** | Equipo del proyecto, solo para operación técnica | Sí (interna) |

**Regla de diseño clave:** se separa la **cuenta** (quien inicia sesión) del **perfil de salud** (la persona cuyos datos se registran). Así un menor o un adulto mayor puede tener perfil sin tener cuenta, y una cuenta puede administrar varios perfiles.

### 4.2 Matriz de permisos

Leyenda: **L** lectura · **E** escritura · **A** administración (vínculos y consentimientos) · **—** sin acceso.

| Recurso | Titular | Representante legal | Cuidador (lector) | Cuidador (editor) | Profesional (QR) | Operador |
|---|---|---|---|---|---|---|
| Datos de salud del perfil | L/E | L/E | L | L/E | L (solo categorías compartidas) | **—** |
| Registro de tomas y síntomas | L/E | L/E | L | L/E | L (resumen) | **—** |
| Vínculos y delegación | A | A | — | — | — | — |
| Generar QR | Sí | Sí | No | Sí si el titular lo permite | — | — |
| Bitácora de accesos | L | L | — | — | — | — |
| Exportar y eliminar datos | Sí | Sí (del menor) | No | No | — | — |
| Métricas técnicas anónimas | — | — | — | — | — | L |

**Principio:** el operador de plataforma **nunca** ve contenido de salud. Si el equipo necesita depurar, usa datos sintéticos.

---

## 5. Requisitos funcionales y criterios de aceptación

**Convenciones.** Cada requisito tiene un identificador (`RF-MÓDULO-NN`), una prioridad MoSCoW y criterios en formato *Dado / Cuando / Entonces*. Un requisito se considera **aceptado** solo cuando todos sus criterios pasan con evidencia (prueba automatizada o captura de la verificación manual). La definición de "terminado" está en la sección 12.4.

### Módulo AUT — Cuenta y sesión

**RF-AUT-01 · Registro de cuenta (Debe)**
- *Dado* un correo no registrado y una contraseña de al menos 10 caracteres, *cuando* la persona se registra, *entonces* se crea la cuenta en estado "sin verificar" y se envía un correo de verificación.
- *Dado* un correo ya registrado, *cuando* se intenta registrar, *entonces* el sistema responde sin revelar si el correo existe.
- *Dado* una contraseña débil (corta o en una lista de contraseñas comunes), *cuando* se envía el formulario, *entonces* se rechaza con un mensaje claro.
- La contraseña se guarda solo como hash Argon2id.

**RF-AUT-02 · Verificación de correo (Debe)**
- *Dado* un enlace de verificación vigente (válido por 24 horas y de un solo uso), *cuando* se abre, *entonces* la cuenta pasa a "verificada".
- *Dado* un enlace vencido o ya usado, *cuando* se abre, *entonces* se informa y se ofrece reenviarlo.

**RF-AUT-03 · Inicio y cierre de sesión (Debe)**
- *Dado* credenciales correctas de una cuenta verificada, *cuando* inicia sesión, *entonces* recibe un token de acceso de corta duración (15 minutos) y un refresh token rotativo en cookie `httpOnly`, `Secure`.
- *Dado* 5 intentos fallidos seguidos, *cuando* intenta un sexto, *entonces* se bloquea temporalmente (15 minutos) y se registra el evento.
- *Cuando* cierra sesión, *entonces* el refresh token queda invalidado en el servidor.

**RF-AUT-04 · Recuperación de contraseña (Debe)**
- *Dado* un correo registrado, *cuando* solicita recuperación, *entonces* recibe un enlace de un solo uso válido por 30 minutos, y la respuesta es idéntica exista o no el correo.
- *Cuando* establece la nueva contraseña, *entonces* se invalidan todas las sesiones anteriores y **no se pierden los datos de salud** (ver decisión de llaves en 7.3).

**RF-AUT-05 · Gestión de sesiones (Podría)**
- La persona ve sus sesiones activas y puede cerrarlas.

### Módulo PER — Perfiles de salud y zonas de consulta

**RF-PER-01 · Perfil propio (Debe)**
- *Dado* un titular verificado, *cuando* completa su perfil (nombre, fecha de nacimiento, datos mínimos), *entonces* se crea un perfil asociado a su cuenta.
- El sistema **no solicita** documento de identidad ni datos que no use (minimización).

**RF-PER-02 · Zonas de consulta (Debe)**
- La persona crea, edita y archiva zonas (por ejemplo "Cardiología", "Pediatría", "Clínica X") para categorizar registros.
- *Dado* una zona con registros, *cuando* se archiva, *entonces* sus registros se conservan y siguen consultables.

**RF-PER-03 · Cambio de perfil activo (Debe)**
- Una cuenta con varios perfiles puede cambiar entre ellos y la interfaz **muestra siempre de quién es el perfil activo**.

### Módulo CLI — Registros de salud

**RF-CLI-01 · Diagnósticos (Debe)**
- CRUD de diagnósticos con fecha, descripción, zona y estado (vigente, resuelto).
- *Dado* un registro ajeno (de otro perfil), *cuando* se intenta leer o editar, *entonces* el sistema responde sin revelar su existencia (404).

**RF-CLI-02 · Fórmulas y exámenes con archivos (Debe)**
- Se pueden adjuntar imágenes y PDF (máximo 10 MB cada uno, tipos permitidos validados por contenido y no solo por extensión).
- *Dado* un archivo no permitido o demasiado grande, *cuando* se sube, *entonces* se rechaza con mensaje claro.
- Los archivos se guardan en un almacenamiento privado y se acceden mediante URL firmada que vence en minutos.

**RF-CLI-03 · Línea de tiempo (Debería)**
- Vista cronológica de diagnósticos, fórmulas, exámenes y síntomas con filtro por zona y fecha.

**RF-CLI-04 · Búsqueda (Podría)**
- Búsqueda por texto en los registros del perfil activo.

### Módulo MED — Medicación

**RF-MED-01 · Registrar medicamento y pauta (Debe)**
- Datos: nombre, dosis, vía, frecuencia (cada N horas, horarios fijos, o días específicos), fecha de inicio, duración o "continuo", indicaciones.
- *Dado* una pauta "cada 8 horas por 5 días" iniciada hoy a las 08:00, *cuando* se guarda, *entonces* se generan las tomas programadas a las 08:00, 16:00 y 00:00 durante 5 días en la zona horaria America/Bogotá.

**RF-MED-02 · Lista "Hoy toca" (Debe)**
- Muestra las tomas del día en orden, con estado: pendiente, tomada, omitida o pospuesta.
- *Cuando* se marca una toma, *entonces* queda registrada con la hora real y el perfil que la registró.

**RF-MED-03 · Tomas atrasadas y omitidas (Debe)**
- Una toma pendiente que pasa su ventana (configurable, por defecto 2 horas) se marca "atrasada" y luego "omitida" si no se confirma.
- La adherencia se calcula como tomas tomadas sobre tomas programadas.

**RF-MED-04 · Edición y suspensión de pauta (Debe)**
- *Dado* una pauta modificada, *cuando* se guarda, *entonces* las tomas **futuras** se regeneran y las **pasadas** se conservan sin cambios.

**RF-MED-05 · Inventario y reabastecimiento (Podría)**
- La persona registra existencias y el sistema avisa cuando alcanzan para menos de N días.

### Módulo SIN — Síntomas

**RF-SIN-01 · Registro diario (Debe)**
- Campos: fecha y hora, síntoma (de una lista editable), intensidad (escala 0 a 10), nota opcional.
- *Dado* que no hay conexión, *cuando* se registra, *entonces* se guarda en el dispositivo y se sincroniza al reconectar sin duplicados.

**RF-SIN-02 · Historial y tendencia (Debería)**
- Gráfica de intensidad por síntoma en los últimos 7, 30 y 90 días.

### Módulo VIN — Vínculos, tutores y delegación

**RF-VIN-01 · Crear perfil dependiente de un menor (Debe)**
- *Dado* un adulto verificado, *cuando* crea un perfil para un menor de 18 años, *entonces* debe declarar su parentesco o representación legal y aceptar el consentimiento específico, y queda como **representante legal** con acceso de administración.
- El perfil del menor **no requiere** correo ni contraseña propia.
- La app deja constancia de que no puede verificar legalmente el vínculo.

**RF-VIN-02 · Delegar a un cuidador (Debe)**
- *Dado* un titular adulto, *cuando* invita a otra cuenta con un alcance (lector, editor), *entonces* el invitado debe **aceptar** la invitación, y solo entonces obtiene acceso.
- La invitación vence a los 7 días.

**RF-VIN-03 · Revocar y modificar vínculos (Debe)**
- *Cuando* el titular revoca un vínculo, *entonces* el acceso termina de inmediato y queda registrado en la bitácora.
- Un cuidador puede renunciar a su vínculo.

**RF-VIN-04 · Titular que no puede delegar solo (Debe)**
- Un perfil de menor de 18 solo es administrado por su representante legal. No existe acción de "delegar" que el propio menor pueda ejecutar.

**RF-VIN-05 · Transición a la mayoría de edad (Podría)**
- Al cumplir 18, el sistema notifica y permite al ahora adulto reclamar su perfil con una cuenta propia. Mientras no lo haga, el representante legal conserva el acceso con aviso visible.

### Módulo QRM — Acceso temporal del profesional

**RF-QRM-01 · Generar QR (Debe)**
- *Dado* un usuario con permiso, *cuando* genera un acceso, *entonces* elige **qué categorías compartir** y la duración (15 o 30 minutos), y la app muestra un QR y un **PIN de 6 dígitos**.
- El QR contiene solo un enlace con un token aleatorio de 256 bits. **No contiene datos personales.**
- En la base de datos se guarda **solo el hash** del token.

**RF-QRM-02 · Validar el acceso (Debe)**
- *Dado* un QR vigente, *cuando* el profesional lo abre e ingresa el PIN correcto, *entonces* el token se **consume** y se crea una sesión de solo lectura de corta duración.
- *Dado* un PIN incorrecto 5 veces, *entonces* el token se invalida.
- *Dado* un token vencido, ya usado o revocado, *cuando* se abre, *entonces* se muestra un mensaje genérico sin datos.

**RF-QRM-03 · Vista del profesional (Debe)**
- Solo lectura, solo las categorías elegidas, con aviso visible de que son datos aportados por el paciente.
- La respuesta incluye `Cache-Control: no-store` y `Referrer-Policy: no-referrer`, y la página no carga scripts de terceros.

**RF-QRM-04 · Revocación inmediata (Debe)**
- *Cuando* el paciente revoca un QR activo, *entonces* la sesión del profesional deja de funcionar en la siguiente petición.

**RF-QRM-05 · Bitácora de accesos (Debe)**
- El paciente ve cuándo se generó, abrió, falló o expiró cada acceso, con fecha, hora y tipo de dispositivo (sin datos personales del profesional).

**RF-QRM-06 · Resumen determinista (Debería)**
- Contenido: diagnósticos vigentes, medicamentos activos con dosis, adherencia de los últimos 7 días, síntomas recientes con fecha, alergias.
- **Cada línea muestra la fecha del registro de origen.**
- Resaltado por regla (por ejemplo: un síntoma que aparece 3 o más días seguidos).
- El resumen **no contiene texto generado por IA**.
- *Dado* un perfil sin registros, *cuando* se genera, *entonces* indica "sin información registrada" y no inventa contenido.

**RF-QRM-07 · PDF del resumen (Podría)**
- Versión imprimible del resumen, con fecha y hora de generación.

### Módulo CON — Consentimiento y derechos del titular

**RF-CON-01 · Consentimiento informado versionado (Debe)**
- Antes de registrar datos de salud, la persona ve la política de tratamiento y acepta de forma **expresa y separada** (casilla sin marcar por defecto).
- Se guarda: versión del texto, hash del documento, fecha y hora, finalidad y cuenta que aceptó.
- *Dado* una nueva versión del consentimiento, *cuando* la persona entra, *entonces* debe aceptarla para continuar.

**RF-CON-02 · Consentimiento por finalidad (Debe)**
- Se distinguen finalidades: (a) gestión del registro de salud, (b) notificaciones, (c) compartir mediante QR. Se pueden retirar por separado cuando es técnicamente posible.

**RF-CON-03 · Exportar mis datos (Debe)**
- *Cuando* el titular lo solicita, *entonces* descarga un archivo (JSON y CSV) con todos sus datos y los enlaces a sus archivos.

**RF-CON-04 · Eliminar mi cuenta y mis datos (Debe)**
- *Cuando* el titular lo solicita y confirma con su contraseña, *entonces* hay un período de gracia de 7 días con posibilidad de cancelar, y luego se eliminan definitivamente los datos, archivos y suscripciones push.
- El registro de auditoría se conserva sin datos personales identificables.

**RF-CON-05 · Corrección de datos (Debe)**
- La persona puede editar y corregir cualquiera de sus datos.

### Módulo OCR — Lectura asistida de fórmulas

**RF-OCR-01 · Escanear fórmula (Debería)**
- *Dado* una foto de una fórmula, *cuando* la procesa, *entonces* el reconocimiento ocurre **en el dispositivo** (Tesseract.js, idioma español) y la imagen no se envía al servidor.
- La imagen solo se guarda si la persona decide adjuntarla como evidencia.

**RF-OCR-02 · Confirmación obligatoria (Debería)**
- El resultado se muestra junto a la foto en **campos editables**. Nada se guarda sin que el usuario lo confirme, y se muestra el aviso "Verifica estos datos con tu fórmula original".
- *Dado* un reconocimiento fallido o de baja confianza, *entonces* se ofrece la digitación manual sin bloquear el flujo.

**RF-OCR-03 · Medición de calidad (Debería)**
- El equipo mide y reporta el porcentaje de campos correctamente prellenados sobre un conjunto de prueba (mínimo 20 fórmulas impresas sintéticas). **[DECIDIR]** el umbral objetivo después de la primera medición; como referencia, ≥ 70 % en texto impreso. No se promete rendimiento con letra manuscrita.

### Módulo NOT — Recordatorios

**RF-NOT-01 · Notificaciones push (Debería)**
- *Dado* un permiso otorgado, *cuando* llega la hora de una toma, *entonces* se envía una notificación mediante Web Push (VAPID).
- La app informa que en iOS requiere instalarla en la pantalla de inicio.

**RF-NOT-02 · Exportar a calendario (Debería)**
- La persona descarga un archivo `.ics` con las tomas recurrentes y alarma, para que las dispare el teléfono.

**RF-NOT-03 · Aviso de límites (Debe)**
- La app muestra: "Este recordatorio no reemplaza la indicación médica y puede fallar".

**RF-NOT-04 · Alertas al tutor (Podría)**
- Si una toma crítica queda omitida, se avisa por correo al representante o cuidador, con consentimiento.

### Módulo PWA — Experiencia instalable y offline

**RF-PWA-01 · Instalable (Debe)**
- Manifest y service worker válidos; la auditoría de Lighthouse marca la app como instalable.

**RF-PWA-02 · Registro offline y sincronización (Debe)**
- Funciona sin conexión: ver "Hoy toca", marcar tomas y registrar síntomas.
- *Dado* registros hechos offline, *cuando* vuelve la conexión, *entonces* se sincronizan **sin duplicados** (identificadores generados en el cliente).
- Las tomas y los síntomas son registros de solo adición, por lo que no generan conflictos. Para campos editables se aplica "gana el cambio más reciente" y se informa si hubo conflicto.
- **Limitación documentada:** generar un QR, administrar vínculos y exportar datos requieren conexión.

**RF-PWA-03 · Estado de conexión visible (Debe)**
- La interfaz muestra si hay conexión y cuántos registros están pendientes de sincronizar.

### Módulo ADM — Operación

**RF-ADM-01 · Endpoint de salud y calentamiento (Debe)**
- `GET /health` responde sin datos sensibles y sirve para monitoreo y para despertar el backend.

**RF-ADM-02 · Métricas técnicas anónimas (Podría)**
- Conteo de usuarios, errores y latencias, sin contenido de salud.

---

## 6. Requisitos no funcionales

Cada uno tiene una métrica y un método de verificación. **Los números son metas propuestas** para el equipo; ajústenlas tras la primera medición, pero no las quiten sin justificación.

| Id | Categoría | Requisito | Métrica / verificación |
|---|---|---|---|
| RNF-01 | Seguridad | Contraseñas con Argon2id; sesiones con tokens cortos | Revisión de código y prueba automatizada |
| RNF-02 | Seguridad | Todo el tráfico por HTTPS; cabeceras de seguridad activas | Escaneo de cabeceras (por ejemplo con una herramienta en línea gratuita) |
| RNF-03 | Seguridad | Control de acceso aplicado en el servidor en **cada** endpoint | Pruebas de acceso entre perfiles (sección 13.3) con 0 fallos |
| RNF-04 | Seguridad | Sin vulnerabilidades críticas conocidas en dependencias | `pip-audit` y `npm audit` en CI sin críticas |
| RNF-05 | Privacidad | Sin datos personales de salud en logs, URLs ni herramientas de monitoreo | Revisión de logs en pruebas |
| RNF-06 | Rendimiento | Carga inicial (LCP) menor a 2,5 s en red 4G simulada | Lighthouse |
| RNF-07 | Rendimiento | Latencia p95 de la API menor a 500 ms con 50 usuarios concurrentes (sin contar arranque en frío) | Prueba de carga con Locust |
| RNF-08 | Disponibilidad | Arranque en frío del backend documentado y mitigado | Medición del tiempo de despertar |
| RNF-09 | Usabilidad | Una toma se marca en máximo 2 toques desde "Hoy toca" | Prueba con usuarios |
| RNF-10 | Usabilidad | Puntaje SUS de al menos 68 en el piloto | Cuestionario SUS |
| RNF-11 | Accesibilidad | Cumplir nivel AA de WCAG 2.1 en los flujos principales; contraste suficiente, texto escalable, objetivos táctiles de al menos 44×44 px | Lighthouse (accesibilidad ≥ 90) y revisión manual con lector de pantalla |
| RNF-12 | Compatibilidad | Chrome y Edge (últimas 2 versiones), Safari iOS 16.4 o superior, Firefox; Android 8 o superior | Pruebas manuales en matriz de dispositivos |
| RNF-13 | Offline | El registro de tomas y síntomas funciona sin conexión | Prueba automatizada con red desactivada |
| RNF-14 | Mantenibilidad | Cobertura de pruebas ≥ 70 % global y ≥ 90 % en módulos críticos (auth, permisos, QR, horarios) | Informe de cobertura en CI |
| RNF-15 | Mantenibilidad | Código con linter y formateador sin errores | CI |
| RNF-16 | Portabilidad | Todo el sistema se levanta localmente con un solo comando | `docker compose up` documentado |
| RNF-17 | Documentación | API documentada automáticamente (OpenAPI) | Swagger accesible |
| RNF-18 | Recuperación | Copia de seguridad periódica y restauración probada | Evidencia de una restauración exitosa |
| RNF-19 | Internacionalización | Interfaz en español; fechas y horas en zona America/Bogotá, almacenadas en UTC | Pruebas de zona horaria |

---

## 7. Seguridad y privacidad por diseño

### 7.1 Principios

1. **Minimización:** no se pide ni se guarda lo que no se usa.
2. **Mínimo privilegio:** cada rol y cada token tiene el menor alcance posible.
3. **Defensa en profundidad:** varias capas (autenticación, autorización, cifrado, límites de uso, auditoría).
4. **Privacidad por defecto:** lo compartido es lo que el titular elige expresamente.
5. **Honestidad sobre los límites:** se documenta lo que la seguridad **no** cubre.

### 7.2 Modelo de amenazas resumido

| Amenaza | Control |
|---|---|
| Acceso a datos de otra persona (IDOR) | Verificación de pertenencia o vínculo en el servidor en cada consulta; respuestas 404 uniformes; pruebas dedicadas |
| Robo o reenvío del QR | Token de un solo uso, vigencia corta, PIN aparte, revocación, bitácora |
| Fuerza bruta contra el PIN o el login | Límite de intentos, bloqueo temporal, `slowapi` |
| Filtración de la base de datos | Cifrado de campos sensibles, hash de tokens, sin contraseñas en claro |
| Robo de sesión (XSS/CSRF) | Cookies `httpOnly`/`Secure`/`SameSite`, política de seguridad de contenido (CSP), protección CSRF, escape de salida |
| Carga de archivos maliciosos | Validación de tipo por contenido, límite de tamaño, almacenamiento privado, sin ejecución |
| Dependencias vulnerables | Dependabot, `pip-audit`, `npm audit` |
| Secretos expuestos en el repositorio | Variables de entorno, escaneo con gitleaks, `.env` fuera de Git |
| Fuga por logs o monitoreo | Logs sin datos personales; Sentry (si se usa) con filtrado |

### 7.3 Cifrado y llaves

- **En tránsito:** HTTPS en todo.
- **En reposo:** AES-256-GCM en campos sensibles (diagnósticos, notas, medicamentos, síntomas) mediante un `TypeDecorator` de SQLAlchemy, con identificador de llave para permitir rotación.
- **Llaves:** del lado del servidor, en variables de entorno del proveedor, nunca en el repositorio.
- **Decisión de diseño (importante para la sustentación):** las llaves **no se derivan de la contraseña del usuario**. Esto permite recuperar la cuenta sin perder datos, a cambio de que el sistema **no es de conocimiento cero**: un servidor comprometido, con acceso a las llaves, podría leer los datos. Esa es una limitación que se declara. El cifrado protege ante una **fuga de la base de datos**, no ante un servidor comprometido. **[DECIDIR]** si el equipo asume esta decisión.
- **Archivos:** bucket privado, URLs firmadas de vida corta. Cifrado en reposo del proveedor.

### 7.4 Especificación del acceso por QR

```
1. El paciente elige categorías y duración (15 o 30 min).
2. El servidor genera token = secrets.token_urlsafe(32) y un PIN de 6 dígitos.
3. Se guardan: hash(token), hash(PIN), categorías, expiración, estado.
4. El QR codifica https://<dominio>/q/<token>   (sin datos personales).
5. El profesional abre el enlace e ingresa el PIN.
6. Si es válido: el token se marca "consumido" y se emite una sesión
   de solo lectura de corta duración (por ejemplo 15 min), atada a ese acceso.
7. 5 PIN incorrectos => token invalidado.
8. El paciente puede revocar en cualquier momento; la sesión cae de inmediato.
9. Cada evento (generado, abierto, PIN fallido, consumido, revocado, expirado)
   queda en la bitácora visible para el paciente.
```

Cabeceras de la vista del profesional: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CSP estricta y sin scripts ni recursos de terceros.

**Riesgo residual declarado:** si alguien tiene a la vez el QR y el PIN durante la vigencia, puede acceder. Mitigaciones: vigencia corta, un solo uso, revocación y bitácora.

### 7.5 Autenticación y sesión

- Argon2id (`argon2-cffi`).
- Token de acceso de 15 minutos; refresh token rotativo con detección de reutilización.
- Para que `SameSite` funcione bien, **frontend y API deben compartir dominio principal** (por ejemplo `app.dominio` y `api.dominio`) o servirse detrás de un mismo proxy. Si no, hay que configurar CORS y cookies con cuidado. **[DECIDIR]** en la semana 1 porque afecta el despliegue.
- Verificación de correo obligatoria antes de registrar datos de salud.

### 7.6 Recuperación de cuenta

Ver RF-AUT-04. Si la persona pierde acceso a su correo, **no hay recuperación automática**: se documenta el procedimiento (soporte manual con verificación razonable) o se declara como limitación del piloto.

### 7.7 Auditoría

Tabla de auditoría de solo adición: el rol de base de datos de la aplicación **no tiene permisos de UPDATE ni DELETE** sobre ella. Registra quién accedió, a qué perfil, qué acción, cuándo y desde qué tipo de dispositivo; no registra el contenido de salud.

### 7.8 Copias de seguridad

- Respaldo automático periódico de la base de datos (por ejemplo `pg_dump` programado) guardado cifrado fuera del proveedor principal.
- **Una restauración de prueba documentada antes de la sustentación.**
- Los respaldos con datos reales se tratan con las mismas garantías que la base viva; en el proyecto se usan datos sintéticos.

### 7.9 Plan de respuesta a incidentes

Documento de una página con: qué se considera incidente, a quién se avisa y en cuánto tiempo, cómo se contiene, cómo se comunica a las personas afectadas, y qué se registra. La obligación de reportar incidentes de seguridad a la SIC aplica a responsables del tratamiento; **[VERIFICAR]** con el instructor cómo aplica a un proyecto formativo.

### 7.10 Lista de control OWASP

Revisar el OWASP Top 10 vigente contra el diseño en la semana 8, dejando evidencia por categoría (control de acceso roto, fallos criptográficos, inyección, diseño inseguro, configuración incorrecta, componentes vulnerables, autenticación, integridad, registro y monitoreo, SSRF).

---

## 8. Marco normativo

> **Aviso:** esto es orientación general para el equipo, no asesoría legal. Todo lo marcado **[VERIFICAR]** debe confirmarse con su instructor o un asesor.

| Norma o concepto | Relevancia para Alentia |
|---|---|
| **Ley 1581 de 2012** (protección de datos personales) y su reglamentación (compilada en el Decreto 1074 de 2015) | Marco principal. Exige autorización previa, expresa e informada; finalidades claras; política de tratamiento; y reconoce derechos al titular (conocer, actualizar, rectificar, suprimir, revocar) |
| **Datos sensibles** | Los datos de salud son sensibles. Su tratamiento exige autorización explícita y debe ser facultativo (la persona no está obligada a darlos) |
| **Niños, niñas y adolescentes** | Menores de 18 años. El tratamiento de sus datos exige autorización del representante legal y respeto por el interés superior del menor y sus derechos prevalentes. La jurisprudencia de la Corte Constitucional sobre la Ley 1581 lo desarrolla. **No existe en Colombia un umbral de 13 años**; ese número proviene de la ley estadounidense COPPA **[VERIFICAR]** |
| **Registro Nacional de Bases de Datos (SIC)** | Aplica a ciertos responsables según su tamaño. **[VERIFICAR]** cómo aplica a un proyecto formativo y documentar la respuesta |
| **Historia clínica** (Resolución 1995 de 1999 y Ley 2015 de 2020) | Regulan la historia clínica que llevan prestadores de salud. Alentia **no es historia clínica**; el descargo y el nombre lo reflejan. Si en Fase 2 se integra con IPS, estas normas pasan a ser centrales |
| **Software como dispositivo médico** | Un software que diagnostica o recomienda tratamiento puede regularse. Alentia no lo hace, y por eso el resumen es determinista y se evita la IA generativa. **[VERIFICAR]** con el instructor |
| **Propiedad intelectual y licencias** | Revisar licencias de dependencias y elegir una licencia para el repositorio |

### 8.1 Documentos que el proyecto debe producir

1. **Política de tratamiento de datos personales** (finalidades, derechos, canales, vigencia).
2. **Aviso de privacidad** corto en el registro.
3. **Texto de consentimiento informado**, versionado.
4. **Términos y condiciones de uso**, con el descargo de la sección 1.3.
5. **Procedimiento de atención de derechos del titular** (exportar, rectificar, suprimir) con plazos.
6. **Plan de respuesta a incidentes** (sección 7.9).

### 8.2 Regla de datos en el proyecto

- Desarrollo, pruebas y demostración: **solo datos sintéticos** (generados con Faker en español de Colombia).
- Piloto: participación voluntaria, con consentimiento, y se anima a usar datos ficticios.
- Prohibido usar historiales de familiares reales como datos de prueba.

---

## 9. Arquitectura y stack tecnológico

### 9.1 Vista general

```
[Navegador / PWA instalada]
   React + Vite + Service Worker + IndexedDB (Dexie) + Tesseract.js (OCR local)
            |  HTTPS (JSON)
            v
[API REST — FastAPI]  routers -> servicios -> repositorios
   Auth | Perfiles | Clínico | Medicación | Síntomas | Vínculos | QR | Consentimiento | Notificaciones
            |                         |                        |
            v                         v                        v
   [PostgreSQL]               [Almacenamiento privado]   [Web Push / SMTP]
   (campos cifrados)          (URLs firmadas)

[Cron externo] ---> POST /internal/tick (secreto) ---> genera recordatorios y despierta el backend
```

### 9.2 Decisión de stack, una tecnología por función

| Función | Elección | Plan B | Notas |
|---|---|---|---|
| Frontend | React + Vite + `vite-plugin-pwa` (Workbox) | — | Service worker y manifest casi automáticos |
| Offline | IndexedDB con Dexie + cola de sincronización | — | Identificadores UUID generados en el cliente |
| Backend | FastAPI + Pydantic + SQLAlchemy 2 + Alembic | — | Swagger automático |
| Base de datos | PostgreSQL en Supabase o Neon | SQLite solo para desarrollo local | Verificar pausa por inactividad y límites |
| Archivos | Almacenamiento privado del proveedor de BD | Disco local en demo | Verificar cuota |
| Hosting frontend | Cloudflare Pages, Vercel o Netlify | — | Estático: no se duerme |
| Hosting backend | Render (plan gratuito) | Ejecución local con Docker para la demo | Se duerme tras inactividad |
| OCR | Tesseract.js (`spa`) | Digitación manual | La imagen no sale del dispositivo |
| Push | Web Push con VAPID (`pywebpush`) | Lista "Hoy toca" + `.ics` | Sin Firebase |
| Tareas programadas | cron-job.org llamando a un endpoint protegido | GitHub Actions (revisar minutos gratuitos en repos privados) | Cumple dos funciones: recordatorios y mantener despierto el backend |
| Correo | SMTP de Brevo (nivel gratuito) | Registro en consola en desarrollo | Para verificación y recuperación |
| Límite de peticiones | `slowapi` | — | Protege QR y login |
| Pruebas | Pytest, Vitest, Playwright, Locust, Lighthouse | — | Todo gratuito |
| CI/CD | GitHub Actions + Docker | — | Verificar minutos si el repositorio es privado |
| Errores | Sentry (opcional) con filtrado de datos | Logs propios | Sin datos personales |

> **Los límites y precios de los servicios gratuitos cambian.** Revísenlos en la semana 1 y en la semana 7, y dejen la captura de las condiciones como evidencia.

### 9.3 Decisiones arquitectónicas que deben documentarse como ADR (anexo C)

- ADR-01: FastAPI como único backend.
- ADR-02: Cuenta separada de perfil de salud.
- ADR-03: Resumen determinista en lugar de IA generativa.
- ADR-04: OCR local en lugar de API externa.
- ADR-05: Llaves de cifrado del lado del servidor y no derivadas de la contraseña.
- ADR-06: Web Push + `.ics` + lista en la app, en lugar de depender de un solo canal.
- ADR-07: Dominio compartido para frontend y API (cookies).
- ADR-08: Dexie y registros de solo adición para sincronización offline.

### 9.4 Estructura de repositorio propuesta

```
alentia/
  backend/
    app/
      api/v1/           # routers
      core/             # config, seguridad, cifrado
      models/           # SQLAlchemy
      schemas/          # Pydantic
      services/         # reglas de negocio (horarios, QR, resumen)
      repositories/
    alembic/
    tests/
  frontend/
    src/
      features/         # auth, perfiles, medicación, síntomas, qr...
      lib/              # api client, db (dexie), sync, ocr
      sw/               # service worker
    tests/
  docs/                 # documentos del proyecto, ADR, diagramas
  .github/workflows/
  docker-compose.yml
  CONTRIBUTING.md  CHANGELOG.md  LICENSE  README.md
```

---

### 9.5 Estado de avance del código (corte 13 de octubre de 2026)

| Paso | Contenido | Estado | Evidencia |
|---|---|---|---|
| 1 | Esqueleto del backend, `/health`, cabeceras de seguridad, Docker | Completado | Pruebas de cabeceras y salud |
| 2 | PostgreSQL 16, modelos, migración inicial, cifrado AES-256-GCM con rotación de llaves, tablas de solo adición | Completado | Migraciones 0001 y 0002; pruebas de cifrado y de triggers |
| 3 | Autenticación y sesión (ver tabla siguiente) | Completado con correcciones de revisión | 47 pruebas en PostgreSQL 16; `ruff` sin errores |
| 4 | Perfiles, zonas de consulta y vínculos de cuidador | Completado (ver 9.6 para las diferencias con la especificación inicial) | 68 pruebas en PostgreSQL 16 |
| 5 y 6 | Medicación, tomas, síntomas y diagnósticos (sección 9.7) | Completado (con diferencias documentadas en 9.7) | 29 pruebas de salud; 16 comprobaciones de navegador |
| 7 | Acceso temporal para profesionales con QR y PIN (sección 9.8) | Completado | 18 pruebas de API; 8 comprobaciones de navegador |
| 8 | Consentimiento, exportación, eliminación con periodo de gracia y correcciones (sección 9.9) | Completado | 14 pruebas de API; 9 comprobaciones de navegador |
| 9 | Recordatorios en la aplicación, atrasos, extensión de tomas y calendario (sección 9.10) | Completado; push (RF-NOT-01) y alertas a tutores (RF-NOT-04) no implementados | 15 pruebas de API; 5 comprobaciones de navegador |
| PWA | Instalación, caché, cola sin conexión e indicador (sección 9.11) | Completado | 13 comprobaciones de navegador con red caída simulada |
| ADM | Salud del servicio (`/health`) cumple RF-ADM-01; métricas (RF-ADM-02) no implementadas | Parcial | Prueba de `/health` |

**Total del proyecto al cierre del prototipo:** 144 pruebas de backend sobre PostgreSQL 16, sin omisiones, y `ruff` sin errores. Pruebas de navegador: 18 (cuentas y perfiles), 16 (salud), 8 (acceso), 9 (cuenta), 5 (recordatorios), 7 (sesión y recuperación), 13 (sin conexión) y la prueba de vista móvil.

**Correcciones de la revisión del paso 3 (incluidas en la versión entregada):**

1. **Enumeración de cuentas corregida.** Antes, una cuenta bloqueada respondía 429 y una cuenta inexistente 401, lo que permitía averiguar qué correos están registrados. Ahora el bloqueo responde 401 con el mismo mensaje que una credencial incorrecta, y se registra en auditoría. Hay una prueba que compara ambas respuestas.
2. **Política de seguridad de contenido por ruta.** La API responde con `default-src 'none'`. La documentación interactiva (`/docs`) necesita cargar Swagger UI desde un CDN, así que recibe una política propia que solo permite `'self'` y el CDN indicado. Hay pruebas de ambas cabeceras. **No verificado** en un navegador real.
3. **Permisos mínimos en la base de datos.** El proceso de la API se conecta con el rol `alentia_app`, que solo puede leer y escribir (sin `DROP`, sin `ALTER`, sin ser dueño de tablas). Las tablas `toma_registro`, `sintoma_registro` y `auditoria` no tienen permiso de `UPDATE` ni de `DELETE` a nivel de rol, además del disparador. Esto cierra el hueco de que un usuario con privilegios de dueño pudiera desactivar el disparador. Las migraciones usan un rol aparte (`MIGRATION_DATABASE_URL`). La migración `0003` crea los permisos y es reversible.

**Endpoints implementados al corte del paso 3:**

| Método | Ruta | Función |
|---|---|---|
| GET | `/health` | Estado del servicio |
| POST | `/api/v1/auth/register` | Registro (respuesta uniforme, envía verificación) |
| POST | `/api/v1/auth/reenviar-verificacion` | Reenvío de verificación (respuesta uniforme) |
| POST | `/api/v1/auth/verify-email` | Verificación del correo |
| POST | `/api/v1/auth/login` | Inicio de sesión (Argon2id, bloqueo tras 5 intentos) |
| POST | `/api/v1/auth/refresh` | Rotación del refresh token con detección de reutilización |
| POST | `/api/v1/auth/logout` | Cierre de sesión |
| POST | `/api/v1/auth/forgot-password` | Solicitud de recuperación (respuesta uniforme) |
| POST | `/api/v1/auth/reset-password` | Restablecimiento de contraseña |
| GET | `/api/v1/auth/me` | Datos de la cuenta autenticada |

**Endpoints del paso 4 (implementados):**

| Método | Ruta | Permiso mínimo | Función |
|---|---|---|---|
| POST | `/api/v1/perfiles` | Cuenta verificada | Crear perfil propio o dependiente |
| GET | `/api/v1/perfiles` | Cuenta verificada | Listar perfiles con acceso vigente |
| GET | `/api/v1/perfiles/{id}` | `lector` | Consultar perfil |
| PATCH | `/api/v1/perfiles/{id}` | `editor` | Actualizar nombre o fecha de nacimiento |
| GET | `/api/v1/perfiles/{id}/zonas` | `lector` | Listar zonas (archivadas con `?incluir_archivadas=true`) |
| POST | `/api/v1/perfiles/{id}/zonas` | `editor` | Crear zona de consulta |
| PATCH | `/api/v1/zonas/{id}` | `editor` | Renombrar o archivar zona |
| GET | `/api/v1/perfiles/{id}/accesos` | `admin` | Listar accesos vigentes (necesario para revocar) |
| POST | `/api/v1/perfiles/{id}/invitaciones` | `admin` | Invitar por correo con un alcance (202) |
| POST | `/api/v1/invitaciones/aceptar` | Cuenta verificada del invitado | Aceptar con el token del correo |
| DELETE | `/api/v1/perfiles/{id}/accesos/{acceso_id}` | `admin` | Revocar acceso (marca `fin`, no borra) |

**Pendientes del paso 3 (no se ocultan):** límite de peticiones con `slowapi` en login y en el futuro QR (la dependencia está en la lista, falta integrarla); envío real de correo con SMTP de Brevo (en desarrollo el correo se registra en consola).

**Verificación en el equipo del desarrollador (Windows con Docker Desktop 4.95, Docker 29.8 y Compose v5.6):** `docker compose` levantó la base de datos y la API, las migraciones se aplicaron, `/docs` carga con sus estilos (la política de contenido por ruta funciona en un navegador real), y el flujo de registro (202), verificación (200), inicio de sesión (200) y la prueba de cifrado con la llave configurada funcionaron. Pendiente: las pruebas automatizadas dentro del contenedor y el envío real de correo.

### 9.6 Especificación del paso 4: perfiles, zonas de consulta y vínculos de cuidador

**Estado: implementado el 13 de octubre de 2026.** Diferencias con la especificación inicial, que se documentan aquí en lugar de ocultarse:

- La regla de menor de 18 años con representante se valida en el servicio, no como restricción en la base de datos. Una restricción equivalente en PostgreSQL requiere un disparador; queda como mejora.
- Se agregó `GET /api/v1/perfiles/{id}/accesos` (alcance `admin`), porque sin él no hay forma de obtener el identificador del acceso que se quiere revocar.
- La migración `0004` convierte `zona_consulta.nombre` a cifrado solo si la tabla está vacía. Un valor en claro no se puede descifrar después. El downgrade elimina la tabla de invitaciones y deja la columna como `TEXT`, porque los valores cifrados no se pueden devolver a texto en claro desde SQL.
- Pruebas: 20 pruebas nuevas de perfiles, zonas, invitaciones y revocación, más 2 de permisos del rol de aplicación. Total del proyecto: 68 pruebas, sin omisiones.


**Objetivo.** Permitir que una cuenta gestione uno o varios perfiles de salud (propios o de dependientes), organice cada perfil en zonas de consulta y comparta el acceso con otra cuenta mediante una invitación, con permisos verificados en cada petición. Cubre los módulos PER (RF de perfiles y zonas) y la parte de VIN (vínculos y delegación) que no requiere consentimiento ni acceso temporal.

**Fuera de alcance del paso 4:** diagnósticos, medicación, síntomas, QR, consentimiento versionado y recordatorios. Cada uno tiene su propio paso.

**Reglas de negocio:**

- Solo el titular de un perfil puede crear invitaciones de alcance `admin`. Un `editor` puede editar el perfil y sus zonas, pero no invitar ni archivar.
- Un `lector` solo consulta. Sin acceso vigente, la API responde **404** (no 403), para no revelar que el perfil existe.
- Un perfil de menor de 18 años exige al menos un `acceso_perfil` con rol `representante` antes de guardarse. La regla se valida en el servicio (ver diferencias al inicio de esta sección).
- La invitación lleva un token aleatorio de 32 bytes; en la base de datos se guarda solo su hash SHA-256 (como `token_accion`). Vence a las 72 horas y se consume una sola vez. **[DECIDIR]** confirmar el plazo con el equipo.
- Las zonas de consulta se archivan y no se borran, para conservar la trazabilidad de los registros que dependen de ellas.
- Todo acceso a un perfil que cambia datos genera una fila en `auditoria`.

**Endpoints previstos:**

| Método | Ruta | Permiso mínimo | Función |
|---|---|---|---|
| POST | `/api/v1/perfiles` | Cuenta verificada | Crear perfil (propio o dependiente) |
| GET | `/api/v1/perfiles` | Cuenta autenticada | Listar perfiles con acceso vigente |
| GET | `/api/v1/perfiles/{id}` | `lector` | Consultar perfil |
| PATCH | `/api/v1/perfiles/{id}` | `editor` | Actualizar datos no sensibles y cifrados |
| POST | `/api/v1/perfiles/{id}/zonas` | `editor` | Crear zona de consulta |
| GET | `/api/v1/perfiles/{id}/zonas` | `lector` | Listar zonas (activas y archivadas con bandera) |
| PATCH | `/api/v1/zonas/{id}` | `editor` | Renombrar o archivar zona |
| POST | `/api/v1/perfiles/{id}/invitaciones` | `admin` | Invitar a otra cuenta con un alcance |
| POST | `/api/v1/invitaciones/aceptar` | Cuenta del invitado | Aceptar con el token recibido por correo |
| DELETE | `/api/v1/perfiles/{id}/accesos/{acceso_id}` | `admin` | Revocar acceso (marca `fin`, no borra) |

**Cambios en datos (migración `0004`):** `zona_consulta.nombre` pasa a cifrado (`TEXT`), y se crea la tabla `invitacion_perfil` (id, perfil_id, correo_invitado, alcance, hash_token único, creada_por, creada_en, vence_en, aceptada_en). Ningún dato existente cambia.

**Criterios de aceptación (verificables con pruebas):**

1. Un usuario sin acceso recibe 404 al consultar, modificar o listar zonas de un perfil ajeno, aun conociendo su identificador.
2. Un `lector` recibe 403 al intentar modificar una zona de un perfil al que sí tiene acceso.
3. Una invitación vencida, ya usada o con token alterado se rechaza con el mismo mensaje genérico.
4. Crear un perfil de menor sin representante se rechaza con error de validación.
5. Revocar un acceso impide la siguiente petición de esa cuenta al perfil, sin esperar a que caduque el token de acceso de 15 minutos (la consulta de permisos se hace en cada petición).
6. El nombre del perfil y de las zonas se guarda cifrado; la prueba lee la columna cruda y comprueba que no contiene el texto en claro.

**Pruebas previstas:** unitarias de reglas (menor, alcance), de integración para cada endpoint con PostgreSQL 16, de autorización cruzada entre dos cuentas (IDOR), y de la migración (subir y bajar).

**Definición de terminado del paso 4:** las pruebas pasan, `ruff` no reporta errores, la migración sube y baja sin error, el README indica el paso como completado y el documento de diseño se actualiza con el estado real.

---

### 9.7 Especificación de los pasos 5 y 6: medicación, tomas, síntomas y diagnósticos

**Estado: implementado el 13 de octubre de 2026.** Pruebas: 29 nuevas en `tests/test_salud_api.py` (total del proyecto: 97, sin omisiones), y 16 comprobaciones en navegador real en `frontend/e2e/salud.mjs`.

**Objetivo.** Registrar la medicación de un perfil con sus tomas programadas, dejar constancia de cada toma (tomada, omitida o pospuesta), y llevar síntomas y diagnósticos con su zona de consulta. Cubre la medicación, los síntomas y los diagnósticos del alcance, sin recordatorios ni notificaciones (paso 9).

**Reglas de negocio aplicadas:**

- Los horarios se escriben en la zona horaria del cliente, pero se guardan en UTC. Si el cliente no envía zona, se usa `America/Bogota` (`ZONA_HORARIA_POR_DEFECTO`). Una zona inválida responde 422.
- Una pauta de horas fijas o de cada N horas genera las tomas de 30 días desde el inicio (o hasta el fin, si se indica). La generación es idempotente: repetir la programación no duplica tomas (restricción `uq_toma_medicamento_hora`).
- Un registro de toma es de solo adición. Corregir una toma crea un registro nuevo y gana el más reciente; el historial se conserva. Esta regla la aplica la base de datos con el disparador de solo adición del paso 3.
- Un registro de toma o de síntoma puede enviar un identificador generado en el cliente. Si la petición se reenvía (por ejemplo, al recuperar la conexión), el servidor devuelve el registro existente y no crea un duplicado. Usar un identificador de otro perfil o de otra toma responde 422.
- Registrar tomas y síntomas requiere alcance `editor`; consultar requiere `lector`. Sin acceso, la API responde 404.
- Nombre, dosis y frecuencia de la pauta, nota de síntoma y descripción de diagnóstico se guardan cifrados (AES-256-GCM, formato `v1:<kid>:<base64>`). Las pruebas verifican que el valor en claro no aparece en la columna.
- Intensidad de síntoma: entero de 0 a 10. La fecha de un síntoma debe incluir zona horaria; si se omite, se usa el momento del registro.
- Consultas por rango de fechas: máximo 62 días por petición.

**Endpoints:**

| Método | Ruta | Permiso mínimo | Función |
|---|---|---|---|
| POST | `/api/v1/perfiles/{id}/medicamentos` | `editor` | Crear pauta y programar sus tomas |
| GET | `/api/v1/perfiles/{id}/medicamentos` | `lector` | Listar pautas (activas e inactivas) |
| PATCH | `/api/v1/medicamentos/{id}` | `editor` | Desactivar o reactivar (no borra) |
| GET | `/api/v1/perfiles/{id}/tomas?desde&hasta&zona_horaria` | `lector` | Tomas con hora local y último estado |
| POST | `/api/v1/tomas/{id}/registros` | `editor` | Registrar tomada, omitida o pospuesta |
| POST | `/api/v1/perfiles/{id}/sintomas` | `editor` | Registrar síntoma |
| GET | `/api/v1/perfiles/{id}/sintomas?desde&hasta&zona_horaria` | `lector` | Listar síntomas del rango |
| POST | `/api/v1/perfiles/{id}/diagnosticos` | `editor` | Registrar diagnóstico (zona opcional) |
| GET | `/api/v1/perfiles/{id}/diagnosticos?incluir_resueltos` | `lector` | Listar diagnósticos |
| PATCH | `/api/v1/diagnosticos/{id}` | `editor` | Marcar vigente o resuelto |

**Cambios en datos:** no hay migración nueva. Las tablas `medicamento`, `toma_programada`, `toma_registro`, `sintoma_registro` y `diagnostico` se crearon en las migraciones 0001 y 0002.

**Diferencias con la especificación inicial:**

- La programación cubre 30 días desde el inicio de la pauta. Una pauta de tratamiento prolongado no tiene tomas más allá de ese plazo hasta que el paso 9 incorpore la extensión automática con tareas programadas.
- La interfaz muestra síntomas de los últimos 7 días. La API acepta rangos de hasta 62 días.
- Las tomas de hoy se calculan con la zona horaria del navegador. Un usuario que viaja y no cambia la zona de su perfil verá las horas de su zona actual; registrar la zona de cada pauta queda como mejora.
- Las pruebas de consentimiento para compartir datos de medicación con otros cuidadores pertenecen al paso 8 y no están incluidas aquí.
- **RF-MED-03 (tomas atrasadas y omitidas) queda parcial.** La API permite marcar una toma como omitida, pero la interfaz no destaca automáticamente las tomas vencidas de días anteriores. **RF-MED-05 (inventario y reabastecimiento)** tiene prioridad «Podría» y no se implementó.

**Verificación:** 29 pruebas de API y de servicio (horarios en UTC, cada N horas, idempotencia de programación y de registros, último registro gana, cifrado en columna, 404 y 403 por alcance, zonas inválidas y rangos fuera de límite). Escenario de navegador con zona America/Bogota: pauta, tomas de hoy, corrección tras recargar, desactivar y reactivar, síntomas, diagnósticos, validación de intensidad y ausencia de desbordamiento horizontal a 375 px.

### 9.8 Especificación del paso 7: acceso temporal para profesionales (QR y PIN)

**Estado: implementado el 13 de octubre de 2026.** Pruebas: 18 de API en `tests/test_acceso_temporal_api.py` y 8 comprobaciones en navegador real en `frontend/e2e/acceso.mjs`.

**Objetivo.** Que un titular comparta con un profesional de salud la información del perfil durante un tiempo corto, sin que el profesional tenga que crear una cuenta. Un código QR abre la página de resumen y un PIN confirma que quien la abre es la persona prevista.

**Reglas de negocio aplicadas:**

- Crear un acceso requiere alcance `editor` y el consentimiento de compartir con profesionales (finalidad `qr`, paso 8). Sin consentimiento, la API responde 403 con el título «Consentimiento requerido».
- La duración solo puede ser de 15 o 30 minutos. Las categorías que se comparten son un subconjunto de diagnósticos, medicamentos y síntomas.
- El enlace (token) y el PIN de seis dígitos no se guardan en claro. El token se guarda con SHA-256 y el PIN con Argon2id. El PIN se muestra una sola vez, al titular, al crear el acceso.
- Tras cinco PIN incorrectos, el acceso queda bloqueado. Cada intento fallido indica los intentos restantes.
- Revocar un acceso, pendiente o ya usado, lo corta de inmediato. Una sesión profesional abierta deja de funcionar y responde «El paciente revocó este acceso».
- Cada acción queda en la bitácora del acceso con su tipo (`generado`, `abierto`, `pin_fallido`, `bloqueado`, `consumido` o `revocado`) y el tipo de dispositivo.
- Las respuestas con datos llevan `Cache-Control: no-store` y `Referrer-Policy: no-referrer`, para que el enlace no quede en historiales ni en cabeceras de referencia.
- El resumen se limita a las categorías permitidas y a los últimos 7 días. Un síntoma que aparece tres días seguidos se marca como destacado. Cada resumen lleva el aviso fijo «Datos aportados por el paciente. No constituyen un diagnóstico médico.»

**Endpoints:**

| Método | Ruta | Permiso mínimo | Función |
|---|---|---|---|
| POST | `/api/v1/perfiles/{id}/accesos-temporales` | `editor` y consentimiento `qr` | Crear acceso; devuelve enlace y PIN (una vez) |
| GET | `/api/v1/perfiles/{id}/accesos-temporales` | `editor` | Listar accesos con su estado |
| GET | `/api/v1/accesos-temporales/{id}/bitacora` | `editor` | Bitácora del acceso |
| POST | `/api/v1/accesos-temporales/{id}/revocar` | `editor` | Revocar acceso |
| POST | `/api/v1/acceso-profesional/abrir` | Público con token | Abrir el enlace y obtener la sesión de PIN |
| POST | `/api/v1/acceso-profesional/verificar` | Público con token | Verificar el PIN y obtener la sesión de lectura |
| GET | `/api/v1/acceso-profesional/resumen` | Sesión profesional | Resumen de las categorías permitidas |

**Diferencias con la especificación inicial:**

- El PIN se entrega al profesional por un canal fuera de la aplicación (por ejemplo, de viva voz). No se envía por correo.
- El límite de peticiones por IP (`slowapi`) sigue pendiente, como en el paso 3. La protección actual es el bloqueo por acceso tras cinco intentos.

### 9.9 Especificación del paso 8: consentimiento, exportación, eliminación y correcciones

**Estado: implementado el 13 de octubre de 2026.** Pruebas: 14 en `tests/test_cuenta_api.py`, más la verificación de consentimiento en las pruebas de salud y de acceso; 9 comprobaciones en navegador real en `frontend/e2e/cuenta.mjs`.

**Consentimiento (RF-CON-01 y RF-CON-02).** Hay tres finalidades: `salud` (registrar datos de salud), `notificaciones` (recordatorios y calendario) y `qr` (compartir con profesionales). Cada una se acepta o se retira por separado desde la pantalla de inicio y desde «Mi cuenta». La política tiene versión (`2026-10-v1`) y un hash de su texto; aceptar una versión anterior responde 422. Sin consentimiento de `salud`, la API no guarda datos de salud (403). Retirar `salud` no se hace con un botón: la API lo rechaza con el mensaje «Para retirar el consentimiento de salud, elimina tu cuenta». El historial de consentimientos es de solo adición.

**Exportación (RF-CON-03).** `GET /api/v1/cuenta/exportacion?formato=json|csv` descarga los datos de la cuenta y de los perfiles con acceso vigente. La respuesta es un archivo adjunto con `Cache-Control: no-store`.

**Eliminación con periodo de gracia (RF-CON-04).** La solicitud exige la contraseña actual (verificada con Argon2id). La cuenta queda marcada para eliminación con siete días de gracia; durante ese plazo se puede cancelar. Al vencer el plazo, la tarea `python -m app.tareas.purgar_cuentas` borra la cuenta, los perfiles de los que la persona es titular (con sus datos de salud) y los accesos de terceros a esos perfiles. La auditoría se conserva sin identificadores de usuario, porque la tabla de auditoría no tiene clave foránea hacia usuarios.

**Correcciones (RF-CON-05).** Los registros de salud son de solo adición. Corregir una toma, un síntoma o un diagnóstico crea un registro nuevo y el historial permanece. La interfaz de medicación y síntomas muestra solo el último estado de cada registro.

**Endpoints:**

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/v1/cuenta/consentimientos` | Estado actual y política vigente |
| POST | `/api/v1/cuenta/consentimientos` | Aceptar o retirar finalidades |
| GET | `/api/v1/cuenta/exportacion?formato=json` o `csv` | Exportación de datos |
| GET | `/api/v1/cuenta/eliminacion` | Estado de la eliminación programada |
| POST | `/api/v1/cuenta/eliminacion` | Solicitar eliminación (con contraseña) |
| POST | `/api/v1/cuenta/eliminacion/cancelar` | Cancelar durante el periodo de gracia |

**Diferencias con la especificación inicial:**

- La eliminación borra también los perfiles propios de una persona con dependientes. La interfaz muestra la fecha en que se eliminará la cuenta, pero no lista los perfiles que se borrarán; esa advertencia queda como mejora.
- El CSV es una sola tabla con columnas `seccion`, `perfil`, `fecha`, `detalle` y `estado`. El JSON conserva la estructura completa por perfil.

### 9.10 Especificación del paso 9: recordatorios, atrasos, extensión de tomas y calendario

**Estado: implementado el 13 de octubre de 2026.** Pruebas: 15 en `tests/test_recordatorios_api.py` y las de salud y acceso que cubren omisiones y extensiones; 5 comprobaciones en navegador real en `frontend/e2e/recordatorios.mjs`.

**Recordatorios dentro de la aplicación (RF-NOT-02).** `GET /api/v1/recordatorios?zona_horaria=` devuelve las tomas que están en curso o vencidas del usuario. Un banner en la parte superior de todas las pantallas las muestra con los botones Tomada y Omitida; se actualiza cada minuto y al registrar una toma. Requiere consentimiento `notificaciones`. Sin ese consentimiento, el banner no aparece.

**Estados de atraso (RF-MED-03).**

- Una toma aparece como **atrasada** desde su hora hasta dos horas después (`ventana_atraso_horas = 2`).
- Si pasan doce horas sin registro (`horas_para_omision = 12`), la tarea la marca como **omitida**. Ese registro lleva `registrada_por` vacío para distinguir una omisión automática de una manual.

**Extensión de tomas (RF-MED-04).** Cuando una pauta activa tiene menos de 14 días de tomas programadas por delante (`UMBRAL_EXTENSION_DIAS = 14`), la tarea programa tomas hasta completar 30 días desde hoy, sin pasar la fecha de fin de la pauta. La programación es idempotente.

**Calendario (RF-NOT-03).** `GET /api/v1/perfiles/{id}/calendario.ics` genera un archivo RFC 5545 con un evento por toma y una alarma, y un aviso fijo de que no sustituye la indicación médica. El texto se escapa y las líneas largas se pliegan a 75 octetos; los finales de línea son CRLF. El calendario no se actualiza solo: la persona lo vuelve a descargar cuando cambian las pautas.

**Tareas programadas.** Hay dos comandos, pensados para un programador de tareas del entorno de despliegue:

- `python -m app.tareas.ejecutar`: aplica las omisiones y las extensiones, y devuelve un resumen (tomas extendidas, tomas omitidas, cuentas eliminadas).
- `python -m app.tareas.purgar_cuentas`: borra las cuentas cuyo periodo de gracia venció.

En este prototipo se ejecutan a mano durante la demostración. La programación en producción queda fuera del alcance de esta entrega.

**Diferencias con la especificación inicial:**

- **RF-NOT-01 (notificaciones push con VAPID) no está implementado.** Requiere permisos del navegador y un servicio de envío que no se pueden probar en este entorno. Los recordatorios son solo dentro de la aplicación.
- **RF-NOT-04 (alertas a tutores) no está implementado.**
- El calendario no usa reglas de recurrencia (RRULE): genera un evento por toma dentro de la ventana programada.
- **RF-MED-05 (inventario y reabastecimiento)** sigue fuera del alcance.

### 9.11 PWA y modo sin conexión (RF-PWA-01 a RF-PWA-03)

**Estado: implementado el 13 de octubre de 2026.** Pruebas: 13 comprobaciones en navegador real en `frontend/e2e/offline.mjs`, que simulan una red caída de verdad.

**Instalación (RF-PWA-01).** La aplicación tiene manifiesto (`manifest.webmanifest`), iconos de 192 y 512 píxeles y un service worker. El service worker se genera en el build (`dist/sw.js`) con la lista de archivos de la aplicación y una versión calculada a partir de su contenido. Solo se registra en producción o en la vista previa; en desarrollo no se usa para no mezclar cachés. Los iconos son provisionales y deben reemplazarse por la marca final.

**Estrategias de caché.**

- La cáscara de la aplicación (HTML, JavaScript, CSS e iconos) se precarga al instalar. Con la red caída, cualquier ruta de la aplicación abre la página principal guardada.
- Perfiles, zonas, medicación, tomas, síntomas y diagnósticos se leen con «red primero»: si la red responde, se guarda una copia; si no, se usa la última copia. Sin copia, la aplicación muestra «Sin conexión» en lugar de un error técnico.
- Las peticiones de acceso profesional, de autenticación, de exportación y el calendario no se guardan.

**Escrituras sin conexión (RF-PWA-02).** Registrar una toma y registrar un síntoma funcionan sin red. Cada registro se guarda en una cola local (IndexedDB) con un identificador generado en el cliente. Al volver la conexión, o al abrir la aplicación, o cada 30 segundos mientras haya pendientes, la cola se envía en orden. El servidor acepta el mismo identificador dos veces sin duplicar el registro, así que un reenvío no crea datos repetidos (pruebas de idempotencia en `tests/test_salud_api.py`). Si el servidor responde con un error de red o de servidor, el envío se detiene y se reintenta más tarde. Si responde con un rechazo definitivo (por ejemplo, un acceso revocado o una toma que ya no existe), el registro se conserva con su motivo para que la persona lo revise y pueda descartarlo.

**Arranque sin red.** La aplicación recuerda el último usuario conocido (identificador, correo y estado de verificación, sin tokens). Sin red, abre con esa sesión en modo sin conexión y vuelve a verificar la sesión al recuperar la red. Al cerrar sesión se borran las lecturas guardadas y el usuario recordado.

**Indicador de estado (RF-PWA-03).** Un bloque en la parte superior muestra si hay conexión, cuántos registros están pendientes (con botón «Enviar ahora») y, si los hay, los rechazados con su motivo. Las tomas y los síntomas pendientes aparecen marcados como «sin enviar» en su pantalla.

**Limitaciones conocidas:**

- «Hoy toca» sin conexión muestra solo lo que se cargó en línea para ese día. Si la persona no abrió la medicación de hoy con red, no hay nada que mostrar.
- Las lecturas guardadas y la cola viven en el dispositivo. La cola no se separa por usuario dentro del mismo navegador: si una persona cierra sesión con pendientes, esos registros se envían con la siguiente sesión, y el servidor los rechaza si no tiene acceso al perfil.
- La prueba de navegador simula la red caída deteniendo la vista previa. En esta versión de Chromium, `context.setOffline` no corta las peticiones del service worker, así que solo con ese método el worker seguía alcanzando el servidor.
- No se usa Background Sync: el reenvío depende de que la aplicación esté abierta o de que se recupere la conexión mientras está en primer plano.

### 9.12 Cambios respecto a la versión 0.4

- Se agregan las secciones 9.8 a 9.11 (pasos 7, 8, 9 y modo sin conexión). La sección 9.5 se actualiza con el estado de cada paso.
- La sección 13.4 (pruebas offline) queda cubierta por `offline.mjs` en las condiciones descritas en 9.11, salvo el fallo a mitad de la sincronización, que se verifica por idempotencia en el backend y no por prueba de navegador.

## 10. Modelo de datos preliminar

Entidades principales (se refinan en la semana 2 hasta tercera forma normal).

**Estado al 13 de octubre de 2026.** Están implementadas y migradas 13 tablas: `usuario`, `token_accion`, `sesion_refresh`, `perfil`, `acceso_perfil`, `zona_consulta`, `invitacion_perfil` (paso 4), `diagnostico`, `medicamento`, `toma_programada`, `toma_registro`, `sintoma_registro` y `auditoria`. Las demás entidades de esta tabla están **planificadas** para los pasos 5 a 9. Donde el nombre físico difiere del propuesto, prevalece el nombre de la base de datos (por ejemplo, `token_accion` cubre verificación y recuperación; el hash de contraseña se guarda en `usuario.hash_contrasena`). El esquema real se documenta con `pg_dump` en el anexo técnico y no con la tabla preliminar.

| Entidad | Propósito | Campos clave |
|---|---|---|
| `usuario` | Cuenta de acceso | id, correo, hash_contraseña, verificado, creado_en, estado |
| `perfil` | Persona cuya salud se registra | id, nombre (cifrado), fecha_nacimiento, titular_usuario_id (nulo si es dependiente) |
| `acceso_perfil` | Vínculo cuenta ↔ perfil | usuario_id, perfil_id, rol (titular, representante, cuidador), alcance (lector, editor, admin), estado, inicio, fin |
| `invitacion` | Delegaciones pendientes | perfil_id, correo_invitado, alcance, vence_en, estado |
| `consentimiento_version` | Textos versionados | id, versión, hash_documento, finalidad, vigente_desde |
| `consentimiento_aceptado` | Evidencia de aceptación | usuario_id, perfil_id, versión_id, aceptado_en, finalidades |
| `zona_consulta` | Categoría de consulta | id, perfil_id, nombre, archivada |
| `diagnostico` | Diagnósticos | id, perfil_id, zona_id, descripción (cifrado), fecha, estado |
| `formula_examen` | Documentos | id, perfil_id, zona_id, tipo, fecha, archivo_id, notas (cifrado) |
| `archivo` | Metadatos de archivos | id, perfil_id, ruta, tipo_mime, tamaño, hash |
| `medicamento` | Pauta | id, perfil_id, nombre, dosis, vía, frecuencia (estructura), inicio, fin, activo |
| `toma_programada` | Tomas calculadas | id, medicamento_id, programada_en (UTC) |
| `toma_registro` | Registro real (solo adición) | id (UUID del cliente), toma_programada_id, estado, registrada_en, registrada_por |
| `sintoma_registro` | Síntomas (solo adición) | id (UUID del cliente), perfil_id, síntoma, intensidad, nota (cifrado), fecha |
| `qr_acceso` | Accesos temporales | id, perfil_id, hash_token, hash_pin, categorías, vence_en, estado, intentos |
| `qr_evento` | Bitácora de QR | qr_id, tipo_evento, fecha, tipo_dispositivo |
| `auditoria` | Registro de solo adición | id, actor, perfil_id, acción, fecha |
| `push_suscripcion` | Dispositivos para push | usuario_id, endpoint, llaves, creado_en |
| `solicitud_derecho` | Exportar, rectificar, suprimir | usuario_id, tipo, estado, fechas |

**Reglas de integridad críticas**
- Un perfil de menor de 18 debe tener al menos un `acceso_perfil` con rol `representante`.
- `toma_registro` y `sintoma_registro` son de solo adición; las correcciones se hacen con un nuevo registro que referencia al anterior.
- Toda consulta de datos de salud filtra por perfiles a los que el usuario tiene `acceso_perfil` vigente.
- Los campos marcados "cifrado" usan AES-256-GCM con identificador de llave.
- `toma_registro`, `sintoma_registro` y `auditoria` impiden `UPDATE` y `DELETE` por disparador (fila a fila) y por permisos del rol de aplicación (migración 0003).

---

## 11. Contrato de API preliminar

Prefijo `/api/v1`. Todas las respuestas de error siguen un formato uniforme (por ejemplo RFC 7807). Cada endpoint tiene prueba de autorización.

| Grupo | Endpoints principales |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/verify-email`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/forgot-password`, `POST /auth/reset-password` |
| Perfiles | `GET/POST /perfiles`, `GET/PATCH /perfiles/{id}` |
| Vínculos | `POST /perfiles/{id}/invitaciones`, `POST /invitaciones/{id}/aceptar`, `DELETE /perfiles/{id}/accesos/{usuario}` |
| Zonas | `GET/POST/PATCH /perfiles/{id}/zonas` |
| Clínico | `GET/POST/PATCH/DELETE /perfiles/{id}/diagnosticos`, `.../formulas`, `.../examenes`, `POST /perfiles/{id}/archivos` |
| Medicación | `GET/POST/PATCH /perfiles/{id}/medicamentos`, `GET /perfiles/{id}/tomas?fecha=`, `POST /tomas/{id}/registro` |
| Síntomas | `GET/POST /perfiles/{id}/sintomas` |
| Sincronización | `POST /sync` (lotes idempotentes por UUID) |
| QR | `POST /perfiles/{id}/qr`, `DELETE /qr/{id}`, `GET /perfiles/{id}/qr/bitacora` |
| Vista profesional | `POST /q/{token}/validar` (PIN), `GET /q/sesion/resumen` |
| Consentimiento | `GET /consentimientos/vigente`, `POST /consentimientos/aceptar` |
| Derechos | `POST /cuenta/exportar`, `POST /cuenta/eliminar`, `POST /cuenta/eliminar/cancelar` |
| Push | `POST /push/suscribir`, `DELETE /push/suscripcion` |
| Operación | `GET /health`, `POST /internal/tick` (protegido por secreto) |

---

## 12. Buenas prácticas de ingeniería

### 12.1 Control de versiones
- Rama `main` protegida; solo se integra mediante *pull request* con **al menos una revisión** de otro integrante y CI en verde.
- Ramas cortas por funcionalidad: `feat/qr-pin`, `fix/toma-zona-horaria`.
- Commits convencionales (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- Versionado semántico y `CHANGELOG.md`. Etiquetas (`tags`) por hito.
- **Todos los integrantes deben tener commits significativos**; es evidencia de trabajo en equipo.

### 12.2 Calidad de código
- Python: tipado, `ruff` (lint y formato), `mypy` en los módulos críticos.
- JavaScript/TypeScript: ESLint y Prettier. **[DECIDIR]** si usan TypeScript; es recomendable por seguridad de tipos, pero considera la curva de aprendizaje.
- `pre-commit` con los linters y escaneo de secretos (`gitleaks`).
- Arquitectura por capas: los routers no contienen reglas de negocio.
- Validación de entradas con Pydantic; manejo de errores centralizado.
- Configuración con variables de entorno (`pydantic-settings`), principio de 12 factores.
- Migraciones con Alembic; nunca se modifica la base a mano.

### 12.3 Integración y entrega continuas
Pipeline en cada *pull request*:
1. Instalar dependencias y compilar.
2. Lint y formato.
3. Pruebas unitarias e integración (PostgreSQL como servicio).
4. Cobertura con umbral mínimo.
5. Auditoría de dependencias (`pip-audit`, `npm audit`).
6. Escaneo de secretos.
7. Construcción de imágenes Docker.
8. Al fusionar a `main`: despliegue automático a producción (o a *staging* y luego a producción).

### 12.4 Definición de "listo" (DoR) y "terminado" (DoD)

**Historia lista para empezar (DoR):** tiene criterios de aceptación, está estimada, no depende de algo bloqueado y alguien la entiende.

**Historia terminada (DoD):**
- [ ] Criterios de aceptación verificados.
- [ ] Pruebas automatizadas escritas y en verde.
- [ ] Revisión de otro integrante aprobada.
- [ ] Sin vulnerabilidades críticas nuevas ni secretos en el código.
- [ ] Documentación actualizada (API, README o ADR si aplica).
- [ ] Probada en el entorno de despliegue.
- [ ] Accesibilidad básica revisada en la pantalla afectada.
- [ ] No registra datos personales en logs.

### 12.5 Docker
- Imágenes multietapa, usuario sin privilegios, sin secretos en la imagen.
- `docker compose` para levantar API, base de datos y frontend en local con un comando.
- Chequeo de salud (`healthcheck`) en el contenedor.

### 12.6 Registro y observabilidad
- Logs estructurados (JSON), con identificador de petición, **sin datos personales ni de salud**.
- Alertas simples: caída del servicio, tasa de errores.

### 12.7 Documentación
- README con instalación en 5 pasos.
- `CONTRIBUTING.md` con flujo de ramas, estilo y revisión.
- OpenAPI/Swagger actualizado automáticamente.
- ADR por decisión importante.
- Diagramas actualizados: casos de uso, entidad-relación, arquitectura, secuencia del QR.
- Licencia de repositorio **[DECIDIR]** (por ejemplo MIT o AGPL) y verificación de licencias de dependencias.

### 12.8 Prácticas de equipo
- Reunión corta semanal de planificación y revisión, con acta.
- Tablero (GitHub Projects o Trello) con columnas: Pendiente, En curso, En revisión, Hecho.
- Rotación de la revisión de código para que todos conozcan todo el sistema.
- Cada integrante debe poder explicar cualquier módulo en la sustentación.

---

## 13. Estrategia de pruebas

### 13.1 Pirámide

| Nivel | Herramienta | Qué cubre |
|---|---|---|
| Unitarias | Pytest, Vitest | Reglas de negocio: horarios de medicación, cálculo de adherencia, generación del resumen, validaciones |
| Integración | Pytest + PostgreSQL | Endpoints, permisos, cifrado de columnas, migraciones |
| Extremo a extremo | Playwright | Registro, login, registrar medicamento, marcar toma, generar y usar QR, flujo offline |
| Carga | Locust | Latencia con 50 usuarios concurrentes |
| Accesibilidad y PWA | Lighthouse | Instalable, rendimiento, accesibilidad |
| Usabilidad | Piloto + SUS | Experiencia real |

### 13.2 Casos críticos de horarios de medicación (alto riesgo de errores)
- "Cada 8 horas por 5 días", "cada 12 horas continuo", "lunes, miércoles y viernes", "una vez al día en la noche".
- Cambio de hora o zona horaria del dispositivo.
- Toma marcada offline y sincronizada más tarde.
- Pauta editada a mitad de tratamiento (pasado intacto, futuro regenerado).
- Toma atrasada que cruza la medianoche.

### 13.3 Pruebas de seguridad obligatorias
**Control de acceso (la prueba más importante):**
- Para **cada** endpoint con `perfil_id`: un usuario sin vínculo recibe 404, un cuidador lector no puede escribir, un vínculo revocado pierde acceso inmediato.
- Un menor no puede delegar.

**QR:**
- Token reutilizado → rechazado.
- Token vencido → rechazado con mensaje genérico.
- PIN incorrecto 5 veces → token invalidado.
- Revocación → la sesión cae en la siguiente petición.
- Categorías no compartidas → no aparecen en la respuesta.
- El token no aparece en logs ni en cabeceras `Referer`.
- Solo el hash del token existe en la base.

**Autenticación:**
- Bloqueo tras intentos fallidos; enlaces de verificación y recuperación de un solo uso; rotación del refresh token.

**Otros:** carga de archivos inválidos, inyección SQL y XSS en campos de texto, cabeceras de seguridad.

### 13.4 Pruebas offline
- Con red desactivada: marcar tomas y registrar síntomas funciona.
- Al reconectar: sin duplicados, con orden correcto y con indicador de pendientes.
- Fallo a mitad de la sincronización: reintento idempotente.

### 13.5 Evidencias
Cada ejecución importante deja un informe (cobertura, resultados de Playwright, reporte de Lighthouse, captura de Locust). Se guardan en `docs/evidencias/` con fecha.

---

## 14. Despliegue, operación y continuidad

### 14.1 Entornos
- **Local:** `docker compose up`.
- **Staging (opcional):** rama `develop` o previsualización automática.
- **Producción:** rama `main`.

### 14.2 Arranque en frío del backend gratuito
- Al abrir la pantalla "Generar QR", el frontend hace una llamada ligera a `/health` para despertarlo.
- El cron externo llama a `/health` cada pocos minutos durante el horario de uso y especialmente **antes y durante la sustentación**.
- Se mide y documenta el tiempo de despertar.

### 14.3 Plan B de la demostración (obligatorio)
1. Video grabado de la demostración completa.
2. Datos sintéticos precargados.
3. Versión local con Docker lista en un portátil, sin internet.
4. Captura de cada flujo clave.
5. Segundo dispositivo con la PWA instalada.

### 14.4 Mantenimiento tras la entrega
- Responsable nombrado para correcciones y actualizaciones de dependencias.
- Revisión mensual de Dependabot.
- Qué hacer si un servicio gratuito cambia sus límites (migración documentada).
- Política de versiones y de soporte durante la etapa de mantenimiento.

### 14.5 Escalabilidad (cómo crece sin reescribirse)
- API sin estado, lista para varias réplicas.
- Archivos en almacenamiento de objetos.
- Tareas programadas movibles a una cola (por ejemplo Redis + worker) cuando el volumen lo requiera.
- Separación de módulos que facilita extraer servicios si fuera necesario.

---

## 15. Gestión del proyecto y cronograma

### 15.1 Metodología
Scrum ligero: iteraciones semanales, tablero visible, revisión y retrospectiva breve cada viernes. **[VERIFICAR]** si su instructor exige una metodología o formato de actas específico.

### 15.2 Roles del equipo (sugerencia)

| Integrante | Responsabilidad principal | Responsabilidad secundaria |
|---|---|---|
| A | Backend, autenticación, seguridad | Revisión de PR de datos |
| B | Frontend PWA, offline, accesibilidad | Pruebas E2E |
| C | Base de datos, medicación, OCR, pruebas de backend | Revisión de PR de frontend |
| D | DevOps, CI/CD, documentación, investigación de usuarios | Backups y despliegue |

Todos escriben código y todos documentan lo suyo.

### 15.3 Calendario por semana

Festivos probables en el período (**[VERIFICAR]** el calendario oficial): 12 de octubre, 2 de noviembre, 16 de noviembre y 8 de diciembre. El 8 de diciembre cae en la ventana de entrega.

| Semana | Fechas | Foco | Hito de salida |
|---|---|---|---|
| 1 | 5–9 oct | Decisiones (stack, dominio, nombre), verificar servicios gratuitos, repositorio y CI, 3 entrevistas, historias de usuario | Repositorio con CI en verde; acta de decisiones |
| 2 | 12–16 oct (lunes festivo) | Modelo de datos (3FN), casos de uso, prototipos, política de datos, 2 entrevistas más | Documentos de análisis y diseño aprobados |
| 3 | 19–23 oct | Autenticación, perfiles, cifrado, consentimiento | Registro, login y consentimiento funcionando |
| 4 | 26–30 oct | Zonas, diagnósticos, fórmulas y exámenes, archivos | Bóveda básica funcionando |
| 5 | 2–6 nov (lunes festivo) | Medicación y tomas, síntomas, sincronización offline | Núcleo clínico con offline |
| 6 | 9–13 nov | Vínculos, tutores, menores, delegación | Roles completos |
| 7 | 16–20 nov (lunes festivo) | **QR seguro y bitácora**, vista del profesional, PWA instalable, OCR, push y `.ics` | **Congelación de alcance** |
| 8 | 23–27 nov | Pruebas de seguridad, carga y accesibilidad, despliegue, piloto con SUS, copias de seguridad probadas | Aplicación en producción y resultados del piloto |
| 9 | 30 nov–4 dic | **Sin funciones nuevas**: documentación final, corrección de errores, ensayo de sustentación, plan B | Entrega lista antes del 5 de diciembre |

**Holgura:** hay festivos en las semanas 2, 5 y 7, y la entrega cae cerca de otro. Si algún hito se atrasa, se recorta de "Debería" y "Podría", nunca de seguridad ni pruebas.

### 15.4 Indicadores de seguimiento
- Historias terminadas contra planificadas por semana.
- Cobertura de pruebas.
- Defectos abiertos por severidad.
- Commits y revisiones por integrante.

---

## 16. Matriz de riesgos

| # | Riesgo | Prob. | Impacto | Mitigación | Plan de contingencia |
|---|---|---|---|---|---|
| R1 | Sobrealcance | Alta | Alto | MoSCoW, congelación en semana 7, recorte de "Debería/Podría" | Entregar núcleo sólido y documentar el resto como roadmap |
| R2 | Falla de acceso entre perfiles (IDOR) | Media | Muy alto | Autorización centralizada y pruebas por endpoint | Bloquear lanzamiento hasta cero fallos |
| R3 | Uso indebido del QR | Media | Alto | Un solo uso, PIN, vigencia corta, revocación, bitácora | Revocación global de accesos |
| R4 | Alarmas no confiables en PWA | Alta | Medio | Tres canales (push, lista, `.ics`) y aviso de límites | Documentar la limitación |
| R5 | OCR lee mal una dosis | Alta | Alto | Confirmación obligatoria y aviso | Digitación manual |
| R6 | Incumplimiento de la Ley 1581 | Media | Alto | Consentimiento, política, derechos del titular, minimización | Asesoría del instructor |
| R7 | Cambio en servicios gratuitos | Media | Medio | Verificación en semanas 1 y 7; plan B local | Migrar a otro proveedor |
| R8 | Backend dormido durante la demo | Alta | Alto | Cron, `/health`, plan B local | Demo con Docker local |
| R9 | Integrante ausente o desbalance de carga | Media | Alto | Revisión cruzada, documentación del código | Reasignar y recortar alcance |
| R10 | Falta de usuarios para validar | Media | Medio | Reclutar desde la semana 1 | Pruebas con compañeros y familiares con datos ficticios |
| R11 | Pérdida de datos | Baja | Alto | Copias de seguridad y restauración probada | Restaurar desde respaldo |
| R12 | Conflicto de marca con el nombre | Baja | Medio | Verificar en SIC y tiendas | Cambiar nombre (reemplazo de texto) |
| R13 | Errores en horarios de medicación | Media | Alto | Pruebas unitarias tempranas con casos de 13.2 | Corrección prioritaria |
| R14 | Documentación atrasada | Alta | Alto | Documentar mientras se construye; semana 9 sin código | Reservar tiempo de equipo |

---

## 17. Entregables documentales y mapeo a la evaluación SENA

> **Pendiente crítico:** todavía no tenemos la guía del proyecto formativo ni la rúbrica de la ficha. Esta tabla es una propuesta basada en el ciclo de vida del software. Cuando consigan los documentos oficiales, hay que **mapear cada entregable a su resultado de aprendizaje y a su evidencia (conocimiento, desempeño, producto)** y completar la última columna. **[VERIFICAR]**

| Entregable | Contenido | Sección de este documento | Resultado de aprendizaje / evidencia (completar) |
|---|---|---|---|
| Planteamiento y justificación | Problema, objetivos, alcance | 2, 3 | |
| Estudio de usuarios | Entrevistas, personas, hallazgos | 18 | |
| Especificación de requisitos | Funcionales, no funcionales, criterios | 5, 6 | |
| Casos de uso y diagramas | Actores, casos de uso, secuencia del QR | 4, 5 | |
| Modelo entidad-relación y diccionario de datos | Tablas, normalización, reglas | 10 | |
| Arquitectura | Capas, API, seguridad, ADR | 9, 7 | |
| Prototipos y diseño de interfaz | Wireframes, guía de estilo, accesibilidad | RNF-09 a RNF-11 | |
| Código fuente y repositorio | Ramas, commits, revisiones | 12 | |
| Plan y resultados de pruebas | Casos, evidencias, cobertura | 13 | |
| Despliegue y operación | Pipeline, backups, plan de incidentes | 14 | |
| Documentos legales | Política, consentimiento, términos | 8.1 | |
| Manual de usuario y manual técnico | Instalación, uso, mantenimiento | 12.7, 14 | |
| Informe de validación | Piloto, SUS, métricas | 18 | |
| Gestión del proyecto | Cronograma, actas, tablero, riesgos | 15, 16 | |
| Presentación y demostración | Guion, video de respaldo | 19 | |

---

## 18. Plan de validación con usuarios

### 18.1 Entrevistas de descubrimiento (semanas 1–2)
- **Mínimo 5**: al menos 2 cuidadores de menores o adultos mayores, 2 personas con tratamiento continuo y, si es posible, 1 profesional de salud que dé su opinión sobre el resumen (como asesoría informal, no como cliente).
- Duración 20–30 minutos, con consentimiento verbal o escrito.
- Guion base: ¿cómo organizas hoy tus fórmulas y resultados? ¿cómo recuerdas tus medicamentos? ¿qué pasó la última vez que olvidaste algo? ¿qué le muestras al médico? ¿qué te preocuparía de guardar esta información en una aplicación?
- Resultado: personas (arquetipos), hallazgos y requisitos derivados.

### 18.2 Piloto (semana 8)
- 5 a 10 personas con tareas guiadas: registrarse, aceptar el consentimiento, registrar un medicamento, marcar una toma, registrar un síntoma, generar un QR y verlo como "médico", instalar la PWA.
- Medir: tasa de éxito por tarea, tiempo por tarea, errores, **puntaje SUS**, comentarios.
- Datos ficticios por defecto.

### 18.3 Informe
Hallazgos, cambios realizados y mejoras pendientes. Si el resultado es malo, se documenta lo aprendido; eso también es un resultado válido.

---

## 19. Plan de sustentación

### 19.1 Estructura sugerida (≈ 20 minutos)
1. Problema y usuarios (2 min) con un hallazgo real de las entrevistas.
2. Solución y diferenciadores (3 min).
3. Demostración en vivo (6 min): tomar medicamento offline → sincronizar → generar QR → vista del profesional → bitácora → revocar.
4. Arquitectura y decisiones (4 min), con 3 ADR.
5. Seguridad, privacidad y límites (3 min).
6. Pruebas y resultados del piloto (2 min).
7. Roadmap y mantenimiento (1 min).

### 19.2 Preguntas probables y respuesta preparada

| Pregunta | Idea de respuesta |
|---|---|
| ¿Esto es una historia clínica? | No. Es un registro personal gestionado por el paciente, sin validez clínica; el descargo está en la app |
| ¿Quién responde si el OCR se equivoca? | El OCR solo propone; el usuario confirma cada campo con la foto al lado |
| ¿Por qué no usaron IA para el resumen? | Un modelo generativo puede inventar u omitir datos; en salud eso es un riesgo. Elegimos reglas verificables y mostramos la fuente de cada dato |
| ¿Qué pasa si roban el QR? | Un solo uso, PIN aparte, vigencia corta, revocación y bitácora. Reconocemos el riesgo residual |
| ¿Dónde se guardan los datos y quién puede leerlos? | Diagrama de flujo de datos; cifrado en tránsito y en reposo; el equipo no accede a contenido de salud |
| ¿Cómo manejan los datos de menores? | Representante legal con autorización registrada; en Colombia el umbral es 18, no 13 |
| ¿Qué pasa si pierdo mi contraseña? | Recuperación por correo sin pérdida de datos; el costo es que no es de conocimiento cero, y lo documentamos |
| ¿Qué pasa si la alarma no suena? | Hay tres canales y un aviso explícito de que no reemplaza la indicación médica |
| ¿Cómo lo mantienen cuando termine el curso? | Responsable, Dependabot, plan ante cambio de servicios gratuitos |
| ¿Qué quedó por fuera y por qué? | Interoperabilidad con IPS, IA generativa; decisiones justificadas por riesgo y alcance |
| ¿Lo probaron con usuarios? | Entrevistas, piloto y puntaje SUS |
| ¿Qué hizo cada uno? | Cada integrante explica un módulo con su código |

### 19.3 Reglas de oro
- Hablar de **lo que el sistema no hace** y por qué demuestra criterio.
- Todos hablan; nadie lee diapositivas.
- Ensayar tres veces completas con cronómetro y una vez con el plan B.

---

## 20. Checklist pre-sustentación

**Producto**
- [ ] Todos los requisitos "Debe" aceptados con evidencia.
- [ ] Núcleo desplegado y probado desde un teléfono real (Android y iOS si es posible).
- [ ] PWA instalable verificada con Lighthouse.
- [ ] Datos sintéticos precargados, sin datos reales.

**Seguridad y legal**
- [ ] Pruebas de acceso entre perfiles en verde.
- [ ] Pruebas del QR en verde.
- [ ] Sin secretos en el repositorio (historial revisado).
- [ ] Documentos legales publicados (política, consentimiento, términos, descargo).
- [ ] Plan de incidentes redactado.
- [ ] Restauración de copia de seguridad probada.

**Calidad y entrega**
- [ ] CI en verde en `main`; cobertura según metas.
- [ ] README, manuales y OpenAPI al día.
- [ ] Diagramas actualizados.
- [ ] Informe de piloto con SUS.
- [ ] Actas, tablero y commits de **todos** los integrantes.

**Sustentación**
- [ ] Video de respaldo grabado.
- [ ] Versión local con Docker funcionando sin internet.
- [ ] Backend despierto antes de empezar.
- [ ] Respuestas a preguntas probables ensayadas.
- [ ] Documentos mapeados a la rúbrica oficial.

---

## 21. Hoja de ruta (Fase 2) y decisiones pendientes

### 21.1 Fase 2 (solo documental en esta entrega)
- Interoperabilidad con IPS (estándares como HL7 FHIR), con análisis regulatorio completo.
- Aplicación empaquetada para tiendas (por ejemplo con Capacitor).
- Cuenta para profesionales con verificación.
- Alertas inteligentes y gráficos avanzados de adherencia.
- Modelo B2B/SaaS. **No debe escribirse código de Fase 2 antes de la sustentación.**

### 21.2 Decisiones pendientes para esta semana

| # | Decisión | Responsable | Fecha límite |
|---|---|---|---|
| 1 | Nombre definitivo, tras verificación en SIC, tiendas y dominios | Equipo | 9 oct |
| 2 | Dominio compartido para API y frontend (cookies) | Integrante A y D | 9 oct |
| 3 | TypeScript o JavaScript | Integrante B | 9 oct |
| 4 | Asumir o no el cifrado con llaves del servidor (7.3) | Equipo + instructor | 9 oct |
| 5 | Licencia del repositorio | Equipo | 9 oct |
| 6 | Obtener guía del proyecto y rúbrica de la ficha | Integrante D | **Lo antes posible** |
| 7 | Confirmar fecha exacta de entrega y formato | Integrante D | 9 oct |
| 8 | Reclutar a los 5 entrevistados | Todos | 16 oct |
| 9 | Verificar límites actuales de Supabase/Neon, Render, Brevo, cron-job.org | Integrante D | 9 oct |
| 10 | Confirmar con el instructor los puntos **[VERIFICAR]** de la sección 8 | Integrante D | 16 oct |

---

## Anexo A. Glosario

- **PWA:** aplicación web que se instala y puede funcionar sin conexión.
- **PHR:** registro personal de salud, gestionado por el paciente.
- **RBAC:** control de acceso basado en roles.
- **IDOR:** acceso a recursos de otra persona por manipular un identificador.
- **VAPID:** mecanismo de identificación del servidor en Web Push.
- **SUS:** cuestionario estándar de usabilidad de 10 preguntas.
- **ADR:** registro de decisión de arquitectura.
- **MoSCoW:** priorización en Debe, Debería, Podría, No ahora.
- **DoR / DoD:** definición de "listo" y de "terminado".

## Anexo B. Plantilla de historia de usuario

```
Id: HU-XXX        Prioridad: Debe/Debería/Podría      Módulo: ___
Como [rol], quiero [acción] para [beneficio].
Criterios de aceptación:
  - Dado ___, cuando ___, entonces ___.
Requisitos relacionados: RF-___, RNF-___
Notas de seguridad/privacidad: ___
Estimación: ___   Responsable: ___   Revisor: ___
```

## Anexo C. Plantilla de ADR

```
ADR-XX: [título]
Estado: propuesta | aceptada | reemplazada
Contexto: ¿qué problema o fuerza motivó la decisión?
Opciones consideradas: A, B, C (con pros y contras)
Decisión: ___
Consecuencias: ___ (positivas, negativas, riesgos aceptados)
Fecha y responsables: ___
```

---

*Fin del documento v0.1. Próximas versiones: v0.2 tras mapear la rúbrica oficial de la ficha; v0.3 con el modelo entidad-relación y los diagramas de casos de uso.*
