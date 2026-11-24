# DESIGN.md — "Papel, bosque y latón"

Sistema visual del prototipo Shaula_efc. Interfaz **clara** de panel
administrativo institucional: papel cálido, superficies marfil, un riel de
navegación verde bosque y acentos de latón. El modo oscuro queda descartado
como superficie de contenido.

## Estrategia de color

Modo **Operate**: el color codifica acción, selección, estado y wayfinding.
El riel verde es la única gran masa oscura; no es un tema oscuro, es la firma
de navegación. El resto del contenido vive en papel cálido y marfil.

| Token | Valor | Rol |
| --- | --- | --- |
| `--paper` | `#f5f2e8` | Lienzo cálido de la aplicación. |
| `--white` | `#fffdf8` | Paneles, tarjetas y campos. |
| `--surface-2` | `#f7f4ec` | Superficies secundarias. |
| `--surface-3` | `#eef1e6` | Módulos de progreso, selección suave. |
| `--border` | `#dedacd` | Hairlines. |
| `--border-strong` | `#cfccbd` | Bordes de controles. |
| `--ink` | `#1b261f` | Texto principal. |
| `--ink-soft` | `#405147` | Texto secundario. |
| `--ink-muted` | `#53645a` | Metadatos. |
| `--ink-faint` | `#5d6b61` | Etiquetas pequeñas (≥4.5:1). |
| `--green-900` | `#0a2c1e` | Riel, tarjeta NFC, marca. |
| `--green-800` | `#0f3b2a` | Riel y énfasis profundo. |
| `--green-700` | `#14532d` | Acción primaria, selección. |
| `--green-600` | `#1c5a3e` | Hover, acentos. |
| `--green-500` | `#2f6f4f` | Datos y focos. |
| `--sage-300` | `#b9c9b7` | Texto secundario sobre verde. |
| `--sage-100` | `#e9efe2` | Fondos activos claros. |
| `--brass` | `#855a16` | Acento institucional, siguiente paso. |
| `--brass-soft` | `#c9a45a` | Líneas, chip NFC, detalles. |
| `--brass-bg` | `#f6edd7` | Fondo de insignias latón. |
| `--clay` | `#9a4f31` | Rol jefe / énfasis cálido puntual. |
| `--teal` | `#1f6f63` | Rol analista / información. |
| `--red` | `#a33a2a` | Error, intento fallido. |

**Dosificación:** verde y latón solo en el botón primario, el ítem activo, las
barras de datos, el siguiente paso y la tarjeta NFC. El resto es papel, marfil
y tinta cálida. Sin neón, sin glows, sin degradados multicolor.

## Tipografía

- **Manrope** para la interfaz: navegación, labels, botones, tablas y datos.
- **Source Serif 4** solo para titulares de página y del login; aporta el tono
  institucional sin invadir componentes.
- **JetBrains Mono** solo para datos: UID, fechas, horas, porcentajes y números
  de fase. Nunca para párrafos o botones.
- Escala fija: 27 px (saludo), 21–22 px (título de panel), 15 px (topbar),
  14 px (cuerpo), 11–12 px (labels), 9–10 px (metadatos).
- Números tabulares en cifras y KPI.

## Layout

- **Login partido:** contexto del proceso sobre sage cálido a la izquierda;
  formulario en tarjeta marfil a la derecha. Sin tarjeta centrada genérica.
- **Panel:** riel verde de 264 px, topbar marfil de 64 px, contenido máximo
  1260 px sobre papel.
- **Franja de datos única** con divisores de 1 px, no seis tarjetas repetidas.
- Panel principal + riel lateral; timeline de fases a ancho completo.
- Sin eyebrows/kickers sobre títulos.

## Superficies y profundidad

- Paneles marfil con borde cálido, radio 12 px y sombra suave de dos capas.
- Glass solo en la tarjeta de login, con blur bajo.
- Riel verde bosque como navegación; ítem activo en marfil con tinta verde.
- La tarjeta NFC es el único objeto verde oscuro del contenido; chip latón.
- Sombras con offset y blur; nada de halos sin desplazamiento.

## Componentes

- Botón primario: verde bosque `#14532d` → `#1c5a3e`, texto blanco, altura
  42–44 px, `active` escala 0.98, loading con spinner.
- Entradas marfil, borde `#cfccbd`, foco verde de 4 px suave.
- Badges: píldoras claras; verde, latón, teal o arcilla según semántica.
- Estados siempre presentes: hover, focus, active, disabled, loading, error,
  empty.
- La tarjeta NFC es un objeto de producto, no una ilustración.

## Kiosco (Fase 2)

- Cabecera verde bosque de dispositivo con reloj, sonido y acceso al panel.
- Cuerpo papel, tarjeta marfil, controles grandes: tipo ingreso/salida, UID,
  sede y lector.
- La lectura de tarjeta se simula con chips de trabajadores y un campo UID.
- Resultado en panel propio: verde para válida, latón para observada/duplicada,
  arcilla para rechazada.
- Sin sidebar: es una superficie pública y de una sola tarea. La tipografía
  serif da el tono institucional; el mono se reserva para UID, hora y metadatos.

## Incidencias y justificaciones (Fase 3)

- Resumen en cuatro celdas: sin justificar, en revisión, aprobadas y rechazadas.
- Filas de incidencia con tipo, fecha, sede, estado, plazo y acciones; en móvil
  se apilan, nunca se recortan.
- Detalle con línea de tiempo (marcación → incidencia → justificación →
  resolución) y panel de justificación con archivo y decisión.
- Estados: pendiente y en revisión en latón; aprobada en verde jade; rechazada
  en arcilla; cerrada en gris. El color siempre va acompañado de texto.
- El formulario de justificación mantiene el tono de formulario del sistema;
  el archivo es un chip verificable y la decisión del coordinador usa dos
  acciones claras.

## Consolidado y cierre (Fase 4)

- Resumen de periodo en cuatro métricas: trabajadores, horas, incidencias y
  excepciones.
- Tabla de preconsolidado con cabecera fija, números tabulares y scroll interno;
  no se recorta ni se fuerza el ancho de la página.
- Excepciones con formulario de corrección en línea y nota obligatoria.
- Cierre con confirmación explícita, aviso de excepciones y bloqueo irreversible.
- Archivos CSV, Excel y PDF; el PDF usa papel blanco de impresión y la misma
  jerarquía serif/sans, sin depender de recursos externos.
- Estados del periodo: abierto en latón, cerrado en jade, bloqueado en gris.

## Movimiento

- 160 ms, `cubic-bezier(.23,1,.32,1)` para interacción.
- Sin coreografía de carga: la app entra directo a la tarea.
- Solo micro-feedback (hover, press, spinner) y el drawer móvil.
- `prefers-reduced-motion` respetado.

## Superficies del navegador

Selección sage con tinta verde, `caret-color` verde, scrollbar sage, focus
visible, números tabulares.

## Prohibiciones

- Fondo oscuro como superficie de contenido.
- Verde neón, glows o degradados verdes brillantes.
- Violeta, azul o degradados multicolor.
- Eyebrows sobre títulos.
- Rejillas de tarjetas iguales con icono + título + texto como estructura.
- Fondos de cuadrícula decorativos, sparklines o progress rings sin función.
- Mono en párrafos o botones.
- Texto recortado o desbordes horizontales.

## Archivos

- `app/static/css/glass.css`: tokens y controles.
- `app/static/css/app.css`: shell, riel, paneles, fases, errores.
- `app/static/css/login.css`: acceso partido.
- `app/static/js/app.js`: password, flash, loading, drawer.
- `app/templates/`: base, login, panel, errores.
