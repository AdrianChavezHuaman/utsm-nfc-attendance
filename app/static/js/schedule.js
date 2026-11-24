/* Copia el lunes al resto de días laborables en el editor semanal. */
(() => {
  "use strict";

  const formulario = document.querySelector("[data-schedule-form]");
  const boton = document.querySelector("[data-copy-monday]");
  if (!formulario || !boton) return;

  boton.addEventListener("click", () => {
    const lunes = formulario.querySelector('[data-day="0"]');
    if (!lunes) return;
    const entrada = lunes.querySelector('[name="dia_0_entrada"]')?.value;
    const salida = lunes.querySelector('[name="dia_0_salida"]')?.value;
    const turno = lunes.querySelector('[name="dia_0_turno"]')?.value;
    if (!entrada || !salida) return;

    for (let dia = 1; dia <= 4; dia += 1) {
      const bloque = formulario.querySelector(`[data-day="${dia}"]`);
      if (!bloque) continue;
      const activo = bloque.querySelector(`[name="dia_${dia}_activo"]`);
      const entradaDia = bloque.querySelector(`[name="dia_${dia}_entrada"]`);
      const salidaDia = bloque.querySelector(`[name="dia_${dia}_salida"]`);
      const turnoDia = bloque.querySelector(`[name="dia_${dia}_turno"]`);
      if (!activo || !entradaDia || !salidaDia || !turnoDia) continue;
      activo.checked = true;
      entradaDia.value = entrada;
      salidaDia.value = salida;
      turnoDia.value = turno;
    }
  });
})();
