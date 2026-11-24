# Capturas para gestion_v7

Generadas con `make shots-v7` sobre el prototipo local con datos ficticios.
Las imágenes se proponen para el **Anexo A** del documento, con numeración APA.

Formato de leyenda:

> **Figura A1**
> *Acceso al prototipo*
> *Nota.* Fuente: elaboración propia con datos ficticios del prototipo (2026).

| Figura | Archivo | Qué muestra | Uso sugerido |
| --- | --- | --- | --- |
| A1 | `01_login.png` | Acceso al prototipo. Formulario de acceso con el aviso de sesión y las credenciales de demostración. | Cuerpo, seguridad |
| A2 | `02_kiosco.png` | Kiosco NFC. Pantalla de marcación con tarjeta, sede y lector. | Cuerpo, TO-BE |
| A3 | `03_inicio.png` | Panel de inicio. Estado del prototipo, datos maestros y cobertura del flujo. | Cuerpo, solución |
| A4 | `04_dashboard_2024.png` | Indicadores 2024. Línea base AS-IS con huella dactilar. | Cuerpo, diagnóstico |
| A5 | `05_dashboard_2026.png` | Indicadores 2026. Línea base previa al cambio de tecnología. | Cuerpo, diagnóstico |
| A6 | `06_dashboard_2027.png` | Indicadores 2027. Meta TO-BE y enero simulado con NFC. | Cuerpo, evaluación |
| A7 | `07_asistencia.png` | Asistencia diaria. Tablero del día con estados, horarios e incidencias. | Cuerpo, operación |
| A8 | `08_ficha.png` | Ficha individual. Calendario mensual del trabajador con horario y marcas. | Cuerpo, operación |
| A9 | `09_ficha_lista.png` | Ficha en lista. Detalle diario de la ficha individual. | Anexo |
| A10 | `10_mi_asistencia.png` | Vista del trabajador. El trabajador consulta su propia asistencia. | Cuerpo, roles |
| A11 | `11_incidencia_detalle.png` | Detalle de una incidencia. Estado, plazo y trazabilidad de un caso con el plazo vencido. | Cuerpo, justificaciones |
| A12 | `12_justificacion_detalle.png` | Justificación recibida. Sustento digital y decisión del coordinador. | Cuerpo, justificaciones |
| A13 | `13_bandeja.png` | Bandeja del coordinador. Casos del área pendientes de revisión. | Cuerpo, aprobaciones |
| A14 | `14_horarios.png` | Horarios semanales. Una fila por trabajador con su horario vigente. | Cuerpo, operación |
| A15 | `15_horario_semana.png` | Editor de horario. Edición de la semana de un trabajador. | Cuerpo, operación |
| A16 | `16_preconsolidado.png` | Preconsolidado mensual. Resumen del mes y excepciones por corregir. | Cuerpo, cierre |
| A17 | `17_cierre.png` | Cierre del periodo. Autorización del cierre y archivos generados. | Cuerpo, cierre |
| A18 | `18_anual.png` | Consolidado anual. Matriz enero–diciembre y comparativas del caso. | Cuerpo, evaluación |
| A19 | `19_anual_s1.png` | Vista semestral. Primer semestre con totales propios. | Cuerpo, evaluación |
| A20 | `20_marcas.png` | Marcaciones del mes. Listado con sede, lector e incidencia. | Cuerpo, corrección |
| A21 | `21_corregir_marca.png` | Corrección de una marcación. Formulario con fecha, hora, tipo y motivo. | Cuerpo, corrección |
| A22 | `22_auditoria.png` | Auditoría de accesos. Inicios de sesión, intentos fallidos y bloqueos con usuario e IP. | Anexo, trazabilidad |
| A23 | `23_auditoria_correccion.png` | Detalle de una corrección. Lectura humana y cambios antes/después. | Cuerpo, trazabilidad |
| A24 | `24_auditoria_bloqueo.png` | Detalle de un bloqueo. Cuenta bloqueada por intentos fallidos. | Cuerpo, seguridad |
| A25 | `25_admin_usuarios.png` | Administración de usuarios. Cuentas, roles y estado. | Anexo |
| A26 | `26_login_bloqueado.png` | Acceso bloqueado. Mensaje único tras agotar los intentos. | Cuerpo, seguridad |
| A27 | `27_sesion_expirada.png` | Sesión expirada. Aviso de cierre por inactividad. | Cuerpo, seguridad |
| A28 | `28_movil_asistencia.png` | Asistencia en móvil. Tablero diario en 390 px. | Anexo |
| A29 | `29_movil_ficha.png` | Ficha en móvil. Calendario individual en 390 px. | Anexo |
| A30 | `30_movil_anual.png` | Consolidado en móvil. Vista semestral en 390 px. | Anexo |
| A31 | `31_movil_marcas.png` | Marcaciones en móvil. Listado y acción fija en 390 px. | Anexo |

## Notas de uso

- Las capturas 28 a 31 son de 390 px; las demás de 1440 px.
- Las figuras del cuerpo pueden reutilizar estas imágenes con otra numeración;
  el anexo conserva la serie A1–A31.
- La captura 26 usa la misma frase de error que cualquier fallo de acceso, por
  diseño: el sistema no revela si el correo existe.
- La captura 23 corresponde a una corrección real y su restitución, registradas
  en la auditoría del prototipo.
