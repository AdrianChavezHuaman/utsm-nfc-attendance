# Correlación y control del documento v7

**Fecha:** 23/11/2026
**Origen:** `gestion_v6.docx` (sin modificar)
**Salida:** `gestion_v7.docx`

---

## 1. Datos del sistema usados en el texto

| Dato | Valor | Fuente |
| --- | --- | --- |
| Trabajadores | 280 | `trabajador` |
| Tarjetas | 280 | `tarjeta` |
| Marcaciones | 722,242 | `marca` |
| Incidencias | 96,034 | `incidencia` |
| Periodos mensuales | 37 (36 de 2024-2026 y enero 2027) | `periodo` |
| Marcaciones NFC | 18,601, concentradas en enero 2027 | `marca.medio` |
| Marcaciones con huella | 703,641 | `marca.medio` |
| Usuarios | 5 roles | `usuario` |

Las cifras de 2024-2026 son la línea base. Enero de 2027 es una simulación y
no se presenta como medición.

## 2. Tablas que no cambiaron

| Tabla | Contenido | Control |
| --- | --- | --- |
| Tabla 9 | 20/30/40/95 %, 130/125/118/34 h, 15/13.5/12/6 %, 18/16/15/2 %, S/ 2,200/2,100/2,020.40/738.61 | `validar_historico --estricto` |
| Tabla 17 | AS-IS y metas TO-BE | Sin cambios |
| Tabla 27 | Proyección de efectividad | Sin cambios |
| Tabla 29 | Indicadores esperados y adopción NFC | Sin cambios |
| Tabla 30-31 | Costo, ahorro y sensibilidad | Sin cambios |
| Tablas 33-35 | Fichas de los KPI | Cambian solo los semestres |

## 3. Cambios aplicados

- La sección 4.4 pasó de "diseño preliminar pendiente" a "prototipo funcional".
- Se describen las pantallas implementadas y los tres módulos agregados.
- Se actualizó el alcance: Flask, SQLite, 280 trabajadores y 722,242 marcaciones.
- Se agregó 4.4.4 Seguridad del acceso.
- La ficha 33 muestra 90 % y 100 % por semestre; la 34, 40 h y 28 h; la 35, 8 % y 4 %.
- Se agregó una nota que explica el agregado anual: 19/20 = 95 %, 34 h/mes y 6 %.
- Se agregó 5.7 Cómo se verifica la mejora, con la Tabla 36.
- Las conclusiones ya no dicen que el software no existe.
- Se agregó el Anexo A con las figuras A1 a A31.

## 4. Controles de estructura

```
documento ................. abre con python-docx
zip ....................... íntegro
tablas .................... 42 (41 + Tabla 36)
imágenes .................. 38 (7 del v6 + 31 del anexo)
figuras del anexo ......... A1 a A31, en orden
notas de fuente ........... 31
frases del estado anterior  0
capturas incrustadas ...... 31/31
v6 ........................ hash sin cambios
```

## 5. Pendiente al abrir en Word

1. Actualizar el índice con F9 (el documento lo indica en la segunda página).
2. Revisar la paginación del anexo y el tamaño de las figuras.
3. Revisar ortografía y estilo con la vista final.

El script `scripts/actualizar_v7.py` regenera el documento desde el v6. Si se
edita el v7 a mano en Word, no conviene volver a ejecutarlo: reemplazaría esos
cambios.
