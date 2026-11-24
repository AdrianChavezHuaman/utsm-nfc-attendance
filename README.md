# UTSM NFC Attendance · Control de asistencia con tarjeta NFC

Prototipo local de control de asistencia para la **Universidad Tecnológica San Martín (UTSM)**, una institución ficticia de dos sedes. Registra marcaciones con tarjeta NFC, clasifica incidencias, recibe justificaciones digitales, consolida el mes, genera reportes y deja cada cambio en auditoría.

> Proyecto académico con datos ficticios. No es una implantación real ni procesa información de personas.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Tests](https://img.shields.io/badge/tests-135%20passed-1c5a3e)
![Estado](https://img.shields.io/badge/estado-protocolo%20acad%C3%A9mico-855a16)

<p align="center">
  <img src="docs/readme/panel.png" width="49%" alt="Panel de inicio">
  <img src="docs/readme/kiosco.png" width="49%" alt="Kiosco NFC">
</p>
<p align="center">
  <img src="docs/readme/asistencia.png" width="49%" alt="Asistencia diaria">
  <img src="docs/readme/consolidado.png" width="49%" alt="Consolidado anual">
</p>

## Qué puedes hacer

- **Marcar con tarjeta NFC** en un kiosco de sede, con tarjetas de demostración, bloqueo de duplicados y confirmación en pantalla.
- **Revisar la asistencia diaria** de las dos sedes y abrir la ficha de cada trabajador con calendario, lista, horario y horas acumuladas.
- **Gestionar incidencias y justificaciones**: el trabajador sube su sustento, el coordinador de su área aprueba o rechaza y todo queda auditado.
- **Consolidar el mes**: preconsolidado con excepciones, cierre autorizado por jefatura y archivos CSV, Excel y PDF.
- **Analizar el año**: matriz enero–diciembre, comparación enero vs enero, año vs año y vista por semestre.
- **Corregir una marcación** con motivo obligatorio, cierre de la incidencia asociada y registro antes/después.
- **Auditar el sistema** con una lectura humana de cada evento: quién, qué, cuándo, desde qué IP y qué cambió.
- **Administrar** sedes, áreas, trabajadores, tarjetas, lectores, horarios y usuarios.

### Por rol

| Rol | Puede |
| --- | --- |
| **Administrador** | Todo el sistema, incluida la administración de catálogos y usuarios. |
| **Jefe de RR. HH.** | Autorizar el cierre mensual, revisar consolidados y auditar. |
| **Analista de RR. HH.** | Asistencia, personal, consolidado anual, corrección de marcas y auditoría. |
| **Coordinador de área** | Ver su área y resolver las justificaciones de su equipo. |
| **Trabajador** | Consultar su propia asistencia y justificar sus incidencias. |

## Cómo funciona

```text
Tarjeta NFC → lector → API → reglas → marca / incidencia → justificación → consolidado → cierre
```

1. El kiosco envía el UID de la tarjeta y el sistema valida que esté activa.
2. Se aplican las reglas de marcación: duplicados, tolerancia, doble sede y horario.
3. Si algo no cuadra, se crea una incidencia y el trabajador puede justificarla.
4. El coordinador resuelve la justificación; el analista corrige excepciones.
5. El jefe autoriza el cierre y se generan los archivos del periodo.
6. El consolidado anual compara la línea base con la meta y con el escenario simulado.

### Reglas de la marcación

| Regla | Qué controla |
| --- | --- |
| R-01 | Solo tarjetas activas. |
| R-02 | Bloqueo de duplicados en una ventana de 2 minutos. |
| R-03 | Tolerancia de 10 minutos sobre el horario. |
| R-04 | Detección de entrada/salida faltante o fuera de horario. |
| R-05 | Plazo de 5 días hábiles para justificar. |
| R-06 | El coordinador solo resuelve incidencias de su área. |
| R-07 | Un periodo cerrado no admite cambios. |
| R-08 | Una tarjeta perdida se bloquea. |
| R-09 | Alerta por marcaciones en dos sedes en menos de 30 minutos. |
| R-10 | Se conserva la hora real del dispositivo. |

### Arquitectura

- **Flask** con blueprints por módulo: auth, kiosk, incidents, attendance, reports, dashboard, audit, admin y main.
- **SQLAlchemy + SQLite** con 14 tablas: sedes, áreas, trabajadores, tarjetas, horarios, lectores, marcas, incidencias, justificaciones, usuarios, auditoría, periodos, consolidados e indicadores.
- **Jinja2 + CSS propio** con el sistema visual “Papel, bosque y latón”; Chart.js se sirve localmente.
- **WeasyPrint y openpyxl** para PDF y Excel.
- **pytest** para las reglas del proceso y **Selenium** para la evidencia visual.

### Escenarios de datos

| Periodo | Escenario | Marcación |
| --- | --- | --- |
| 2024–2026 | Línea base AS-IS | Huella dactilar, 0 % NFC |
| Enero 2027 | Simulación TO-BE | Tarjeta NFC, 95 % de adopción |
| 2027 anual | Meta TO-BE | No es una medición |

La base de demostración contiene **280 trabajadores**, **2 sedes**, **722,242 marcaciones**, **96,034 incidencias** y **37 periodos mensuales**. Las cifras de 2024 a 2026 son parámetros del caso; enero de 2027 es una simulación.

## Stack

- Python 3.11+ · Flask 3 · SQLAlchemy · Flask-Login · Flask-WTF
- SQLite · Jinja2 · CSS propio · Chart.js local
- WeasyPrint · openpyxl
- pytest · Selenium · ruff

## Estructura

```text
.
├── app/
│   ├── auth/           # acceso, bloqueo y auditoría de sesión
│   ├── kiosk/          # marcación NFC y reglas R-01 a R-10
│   ├── incidents/      # incidencias, justificaciones y aprobaciones
│   ├── attendance/     # asistencia diaria, personal, fichas y horarios
│   ├── reports/        # preconsolidado, cierre, consolidado anual y exportaciones
│   ├── dashboard/      # KPI, series históricas y operación
│   ├── audit/          # registro legible y exportación
│   ├── admin/          # catálogos, tarjetas, lectores y usuarios
│   ├── main/           # inicio y páginas base
│   ├── templates/      # Jinja2
│   └── static/         # CSS, JS, fuentes y Chart.js
├── seeds/              # datos maestros e históricos
├── tests/              # 135 pruebas
├── scripts/            # validación, QA, capturas y migración
├── docs/
│   ├── capturas/v7/    # 31 capturas + manifiesto
│   ├── readme/         # imágenes de esta presentación
│   └── v7/             # control de cifras del documento
├── schema.sql
├── Makefile
├── requirements.txt
└── run.py
```

## Puesta en marcha

Requiere Python 3.11 o superior.

```bash
git clone https://github.com/AdrianChavezHuaman/utsm-nfc-attendance.git
cd utsm-nfc-attendance

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Base maestra: sedes, áreas, 280 trabajadores, tarjetas y usuarios
.venv/bin/flask --app run.py bootstrap

# Línea base 2024-2026 + enero 2027 simulado (puede tardar unos minutos)
make seed-historico

# Servidor local
.venv/bin/python run.py
```

Abre **http://127.0.0.1:5000**.

Atajos equivalentes:

```bash
make setup
make bootstrap
make seed-historico
make run
```

## Cuentas de demostración

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador | `admin@utsm.edu.pe` | `admin123` |
| Jefe de RR. HH. | `jefe@utsm.edu.pe` | `jefe123` |
| Analista de RR. HH. | `analista@utsm.edu.pe` | `analista123` |
| Coordinador de área | `coordinador@utsm.edu.pe` | `coordinador123` |
| Trabajador | `trabajador@utsm.edu.pe` | `trabajador123` |

El administrador ve todo. El analista trabaja con asistencia, personal, consolidado y auditoría. El coordinador solo ve su área y el trabajador solo su ficha.

## Pruebas y calidad

```bash
make test                 # 135 pruebas
make smoke                # 24 comprobaciones de extremo a extremo
make validar-historico    # correlación con la Tabla 9 del documento
make shots-v7             # capturas del anexo (requiere el servidor)
```

- **135 pruebas** de auth, reglas, kiosco, incidencias, reportes, KPI, auditoría, administración e histórico.
- **24/24** comprobaciones de humo.
- **QA visual** a 1440, 390 y 320 px sin desborde horizontal.
- **Auditoría** con lectura humana y JSON técnico plegado.

## Capturas y documentación

- `docs/capturas/v7/`: 31 capturas del prototipo y `MANIFIESTO.md` con la propuesta APA (A1–A31).
- `docs/v7/CORRELACION.md`: control de las cifras del documento frente a la base.
- `DESIGN.md`: tokens y criterios del sistema visual.
- El informe académico se entrega aparte.

<p align="center">
  <img src="docs/readme/ficha.png" width="49%" alt="Ficha individual">
  <img src="docs/readme/auditoria.png" width="49%" alt="Detalle de auditoría">
</p>

## Alcance y límites

- **Datos ficticios**: la UTSM no existe; no son mediciones de una institución real.
- **Sin lector NFC físico**: el kiosco se opera con tarjetas de demostración.
- **Local**: no incluye hosting, PostgreSQL ni integración con planilla.
- **La mejora no está demostrada**: se estima y se deja un piloto de ocho semanas como validación.
- **Seguridad de prototipo**: bloqueo tras cinco intentos, sesión de 30 minutos, cookies `HttpOnly`, `SameSite=Lax` y cabeceras básicas.

## English

A local attendance-control prototype for a fictional university (UTSM). It simulates NFC card check-ins, applies ten business rules, manages incidents and digital justifications, consolidates monthly and annual reports, and records every change in an audit log. Built with Flask, SQLite, Jinja2 and Chart.js; 135 tests and 24 end-to-end checks. All data is fictitious and the improvement is a design estimate, not a measured result.

## Autor

**Adrian Chavez Huaman** · [GitHub](https://github.com/AdrianChavezHuaman)

Proyecto académico de la Facultad de Ingeniería y Arquitectura. Uso educativo.
