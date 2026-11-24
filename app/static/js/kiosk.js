/* Shaula_efc · Kiosco de marcación NFC simulado */
(() => {
  "use strict";

  const form = document.querySelector("[data-kiosk-form]");
  if (!form) return;

  const uidInput = form.querySelector("#uid");
  const sedeSelect = form.querySelector("#sede");
  const lectorSelect = form.querySelector("#lector");
  const submitButton = form.querySelector("[data-kiosk-submit]");
  const submitLabel = form.querySelector("[data-kiosk-submit-label]");
  const resultPanel = document.querySelector("#kiosk-result");
  const soundButton = document.querySelector("[data-sound-toggle]");
  const clockTime = document.querySelector("[data-clock-time]");
  const clockDate = document.querySelector("[data-clock-date]");
  const apiUrl = form.dataset.api || "/api/marca";

  let busy = false;
  let soundOn = true;
  let audioContext = null;

  try {
    soundOn = window.localStorage.getItem("shaula_kiosk_sound") !== "off";
  } catch (_error) {
    soundOn = true;
  }

  // -------------------------------------------------------------------------
  // Sonido
  // -------------------------------------------------------------------------
  function updateSoundButton() {
    if (!soundButton) return;
    soundButton.textContent = soundOn ? "Sonido activo" : "Sonido silenciado";
    soundButton.setAttribute("aria-pressed", String(soundOn));
  }

  function beep(kind) {
    if (!soundOn) return;
    try {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return;
      if (!audioContext) audioContext = new Context();
      if (audioContext.state === "suspended") audioContext.resume();
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      const frequencies = { ok: 880, warn: 620, error: 220 };
      oscillator.type = "sine";
      oscillator.frequency.value = frequencies[kind] || 660;
      gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.1, audioContext.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.2);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.22);
    } catch (_error) {
      /* El sonido es opcional; el resultado visual siempre aparece. */
    }
  }

  if (soundButton) {
    updateSoundButton();
    soundButton.addEventListener("click", () => {
      soundOn = !soundOn;
      try {
        window.localStorage.setItem("shaula_kiosk_sound", soundOn ? "on" : "off");
      } catch (_error) {
        /* almacenamiento no disponible */
      }
      updateSoundButton();
      if (soundOn) beep("ok");
    });
  }

  // -------------------------------------------------------------------------
  // Reloj
  // -------------------------------------------------------------------------
  function updateClock() {
    const now = new Date();
    if (clockTime) {
      clockTime.textContent = new Intl.DateTimeFormat("es-PE", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(now);
    }
    if (clockDate) {
      const texto = new Intl.DateTimeFormat("es-PE", {
        weekday: "long",
        day: "2-digit",
        month: "long",
      }).format(now);
      clockDate.textContent = texto.charAt(0).toUpperCase() + texto.slice(1);
    }
  }

  updateClock();
  window.setInterval(updateClock, 1000);

  // -------------------------------------------------------------------------
  // Lectores: filtra por sede y tipo
  // -------------------------------------------------------------------------
  function tipoSeleccionado() {
    const checked = form.querySelector('input[name="tipo"]:checked');
    return checked ? checked.value : "ingreso";
  }

  function actualizarBoton() {
    if (!submitLabel) return;
    submitLabel.textContent = `Registrar ${tipoSeleccionado()}`;
  }

  function filtrarLectores() {
    if (!sedeSelect || !lectorSelect) return;
    const sede = sedeSelect.value;
    const tipo = tipoSeleccionado();
    const tipoLector = tipo === "ingreso" ? "entrada" : "salida";
    let primera = null;

    Array.from(lectorSelect.options).forEach((option) => {
      const coincide = option.dataset.sede === sede && option.dataset.tipo === tipoLector;
      option.disabled = !coincide;
      option.hidden = !coincide;
      option.style.display = coincide ? "" : "none";
      if (coincide && !primera) primera = option;
    });

    const actual = lectorSelect.selectedOptions[0];
    if ((!actual || actual.disabled) && primera) {
      lectorSelect.value = primera.value;
    }
    actualizarBoton();
  }

  if (sedeSelect) sedeSelect.addEventListener("change", filtrarLectores);
  form.querySelectorAll('input[name="tipo"]').forEach((radio) => {
    radio.addEventListener("change", filtrarLectores);
  });

  // -------------------------------------------------------------------------
  // Entrada de tarjeta
  // -------------------------------------------------------------------------
  if (uidInput) {
    uidInput.addEventListener("input", () => {
      const inicio = uidInput.selectionStart;
      uidInput.value = uidInput.value.toUpperCase();
      if (inicio !== null) uidInput.setSelectionRange(inicio, inicio);
    });
  }

  document.querySelectorAll("[data-uid]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (!uidInput) return;
      uidInput.value = chip.dataset.uid || "";
      uidInput.focus();
      uidInput.select();
    });
  });

  // -------------------------------------------------------------------------
  // Resultado
  // -------------------------------------------------------------------------
  const ESTADOS = {
    valida: { badge: "jade", etiqueta: "Registrado", icono: "tpl-icon-check" },
    observada: { badge: "brass", etiqueta: "Observado", icono: "tpl-icon-alert" },
    duplicado: { badge: "brass", etiqueta: "Duplicado", icono: "tpl-icon-alert" },
    error: { badge: "danger", etiqueta: "Rechazado", icono: "tpl-icon-x" },
  };

  function agregarDetalle(lista, etiqueta, valor, clase) {
    if (!valor) return;
    const fila = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = etiqueta;
    dd.textContent = valor;
    if (clase) dd.className = clase;
    fila.append(dt, dd);
    lista.appendChild(fila);
  }

  function renderResult(data) {
    if (!resultPanel) return;
    const estado = ESTADOS[data.estado] ? data.estado : "error";
    const config = ESTADOS[estado];

    resultPanel.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = `result result--${estado}`;

    const iconWrap = document.createElement("span");
    iconWrap.className = "result-icon";
    const template = document.getElementById(config.icono);
    if (template) iconWrap.appendChild(template.content.cloneNode(true));

    const badge = document.createElement("span");
    badge.className = `badge badge--${config.badge}`;
    badge.textContent = config.etiqueta;

    const title = document.createElement("h2");
    title.textContent = data.titulo || "Resultado";

    const message = document.createElement("p");
    message.textContent = data.mensaje || "";

    wrap.append(iconWrap, badge, title, message);

    if (data.trabajador) {
      const lista = document.createElement("dl");
      lista.className = "result-details";
      agregarDetalle(lista, "Trabajador", data.trabajador);
      agregarDetalle(lista, "Área", data.area);
      agregarDetalle(lista, "Tipo", data.tipo);
      agregarDetalle(lista, "Hora", data.hora, "mono");
      agregarDetalle(lista, "Sede", data.sede);
      agregarDetalle(lista, "Incidencia", data.incidencia_label);
      wrap.appendChild(lista);
    }

    resultPanel.appendChild(wrap);
  }

  function renderError(mensaje) {
    renderResult({
      estado: "error",
      titulo: "Sin conexión",
      mensaje,
    });
  }

  function setBusy(value) {
    busy = value;
    if (!submitButton) return;
    submitButton.classList.toggle("is-loading", value);
    submitButton.setAttribute("aria-busy", String(value));
  }

  form.addEventListener("submit", async (event) => {
    if (!window.fetch || busy) {
      if (busy) event.preventDefault();
      return;
    }
    event.preventDefault();

    const uid = uidInput.value.trim().toUpperCase();
    if (!uid) {
      renderError("Acerca una tarjeta o selecciona una tarjeta de demostración.");
      beep("error");
      uidInput.focus();
      return;
    }
    if (!lectorSelect.value) {
      renderError("Selecciona un lector para continuar.");
      beep("error");
      return;
    }

    const tokenInput = form.querySelector('input[name="csrf_token"]');
    const payload = {
      uid,
      tipo: tipoSeleccionado(),
      id_lector: Number(lectorSelect.value),
    };

    setBusy(true);
    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": tokenInput ? tokenInput.value : "",
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      renderResult(data);
      if (data.estado === "valida") beep("ok");
      else if (data.estado === "error") beep("error");
      else beep("warn");
      if (data.estado !== "error") uidInput.value = "";
    } catch (_error) {
      renderError("No se pudo contactar con el servidor. Verifica que el sistema esté encendido.");
      beep("error");
    } finally {
      setBusy(false);
      uidInput.focus();
    }
  });

  // -------------------------------------------------------------------------
  // Inicio
  // -------------------------------------------------------------------------
  filtrarLectores();
  actualizarBoton();
})();
