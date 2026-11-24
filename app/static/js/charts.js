/* Shaula_efc · Fábrica de gráficos Chart.js y heatmap */
(() => {
  "use strict";

  if (typeof Chart === "undefined" || !document.querySelector(".chart-panel")) return;

  const PALETTE = ["#1c5a3e", "#8fae98", "#855a16", "#9a4f31", "#1f6f63", "#b9c9b7"];
  const charts = new Map();

  Chart.defaults.font.family = '"Manrope", "Segoe UI", system-ui, sans-serif';
  Chart.defaults.font.size = 10;
  Chart.defaults.color = "#52645a";
  Chart.defaults.borderColor = "rgba(23, 37, 29, 0.08)";
  Chart.defaults.animation.duration = 260;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 7;
  Chart.defaults.plugins.legend.labels.boxHeight = 7;

  function hexToRgba(hex, alpha) {
    const value = hex.replace("#", "");
    const numero = Number.parseInt(
      value.length === 3
        ? value.split("").map((c) => c + c).join("")
        : value,
      16,
    );
    const r = (numero >> 16) & 255;
    const g = (numero >> 8) & 255;
    const b = numero & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function filtersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const filtros = {};
    ["anio", "mes", "sede", "area", "tipo"].forEach((clave) => {
      const valor = params.get(clave);
      if (valor) filtros[clave] = valor;
    });
    if (!filtros.anio) filtros.anio = "2026";
    return filtros;
  }

  function chartUrl(serie, tipo, metrica) {
    const params = new URLSearchParams(filtersFromUrl());
    params.set("serie", serie);
    params.set("tipo", tipo);
    if (metrica) params.set("metrica", metrica);
    return `/api/chart-data?${params.toString()}`;
  }

  function setLoading(surface, estado) {
    surface.classList.toggle("is-loading", estado);
  }

  function showChartError(surface, mensaje) {
    let aviso = surface.querySelector(".chart-error");
    if (!aviso) {
      aviso = document.createElement("div");
      aviso.className = "heatmap-empty chart-error";
      surface.appendChild(aviso);
    }
    aviso.textContent = mensaje;
    surface.querySelectorAll("canvas, .heatmap").forEach((elemento) => {
      elemento.hidden = true;
    });
  }

  function shortLabel(label) {
    const texto = String(label)
      .replace(/^Escuela de /, "Esc. ")
      .replace(/^Dirección de /, "Dir. ")
      .replace(/^Oficina de /, "Of. ")
      .replace(/^Departamento de /, "Depto. ");
    return texto.length > 24 ? `${texto.slice(0, 22)}…` : texto;
  }

  function tooltipConfig() {
    return {
      backgroundColor: "#0f3b2a",
      titleColor: "#f3f6ee",
      bodyColor: "#e9f2ea",
      borderColor: "#1c5a3e",
      borderWidth: 1,
      padding: 9,
      cornerRadius: 8,
      displayColors: false,
    };
  }

  function baseOptions(conEjeDoble, horizontal) {
    const scales = {
      x: {
        type: horizontal ? "linear" : "category",
        beginAtZero: horizontal,
        grid: { display: horizontal, color: "rgba(23, 37, 29, 0.07)" },
        ticks: { color: "#6c7b70", maxRotation: horizontal ? 0 : 38, font: { size: 9 } },
        title: {
          display: Boolean(conEjeDoble && horizontal),
          text: "Marcaciones",
          color: "#1c5a3e",
          font: { size: 9, weight: "600" },
        },
      },
      y: {
        type: horizontal ? "category" : "linear",
        beginAtZero: !horizontal,
        grid: { display: !horizontal, color: "rgba(23, 37, 29, 0.07)" },
        ticks: {
          color: "#6c7b70",
          autoSkip: false,
          font: { size: horizontal ? 8.5 : 9 },
          callback(value) {
            if (!horizontal) return value;
            return shortLabel(this.getLabelForValue(value));
          },
        },
      },
    };

    if (conEjeDoble && horizontal) {
      scales.x1 = {
        type: "linear",
        position: "top",
        beginAtZero: true,
        grid: { drawOnChartArea: false },
        ticks: { color: "#9a4f31", font: { size: 9 } },
        title: {
          display: true,
          text: "Incidencias",
          color: "#9a4f31",
          font: { size: 9, weight: "600" },
        },
      };
    } else if (conEjeDoble) {
      scales.y1 = {
        type: "linear",
        position: "right",
        beginAtZero: true,
        grid: { drawOnChartArea: false },
        ticks: { color: "#9a4f31", font: { size: 9 } },
        title: {
          display: true,
          text: "Incidencias",
          color: "#9a4f31",
          font: { size: 9, weight: "600" },
        },
      };
    }

    return {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: horizontal ? "y" : "x",
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: {
            color: "#52645a",
            padding: 14,
            font: { size: 10 },
          },
        },
        tooltip: tooltipConfig(),
      },
      scales,
    };
  }

  function buildDatasets(data, tipo, horizontal) {
    if (tipo === "radial") {
      return data.datasets.map((dataset, indice) => ({
        label: dataset.label,
        data: dataset.data,
        backgroundColor: PALETTE.map((color) => hexToRgba(color, 0.82)),
        borderColor: "#fffdf8",
        borderWidth: 2,
        hoverOffset: 3,
      }));
    }

    const doubleAxis = data.datasets.length > 1;
    const datasets = data.datasets.map((dataset, indice) => {
      const color = dataset.color || PALETTE[indice % PALETTE.length];
      if (tipo === "bar") {
        const ejeSecundario = doubleAxis && indice === 1;
        return {
          type: "bar",
          label: dataset.label,
          data: dataset.data,
          backgroundColor: hexToRgba(color, 0.8),
          borderColor: color,
          borderWidth: 0,
          borderRadius: 4,
          maxBarThickness: 38,
          ...(horizontal
            ? { xAxisID: ejeSecundario ? "x1" : "x" }
            : { yAxisID: ejeSecundario ? "y1" : "y" }),
        };
      }
      return {
        type: "line",
        label: dataset.label,
        data: dataset.data,
        borderColor: color,
        backgroundColor: tipo === "area" ? hexToRgba(color, 0.16) : color,
        fill: tipo === "area",
        tension: 0.32,
        borderWidth: 2.2,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#fffdf8",
        pointBorderColor: color,
        pointBorderWidth: 1.6,
        yAxisID: doubleAxis && indice === 1 ? "y1" : "y",
      };
    });

    if (data.serie === "historico" && data.meta && typeof data.meta.meta === "number") {
      datasets.push({
        type: "line",
        label: `Meta ${data.meta.meta} ${data.meta.unidad || ""}`.trim(),
        data: data.labels.map(() => data.meta.meta),
        borderColor: "#855a16",
        backgroundColor: "#855a16",
        borderDash: [4, 4],
        borderWidth: 1.4,
        pointRadius: 0,
        fill: false,
        tension: 0,
        yAxisID: "y",
      });
    }
    return datasets;
  }

  function drawChart(canvas, tipo, data) {
    if (charts.has(canvas)) {
      charts.get(canvas).destroy();
      charts.delete(canvas);
    }

    const radial = tipo === "radial";
    const horizontal =
      tipo === "bar" && data.serie === "operacion" && data.labels.length > 8;
    const datasets = buildDatasets(data, tipo, horizontal);
    const options = radial
      ? {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "58%",
          plugins: {
            legend: {
              display: true,
              position: "bottom",
              labels: { color: "#52645a", padding: 12, font: { size: 10 } },
            },
            tooltip: tooltipConfig(),
          },
        }
      : baseOptions(
          data.datasets.length > 1 && data.serie === "operacion",
          horizontal,
        );

    const grafico = new Chart(canvas, {
      type: radial ? "doughnut" : tipo === "bar" ? "bar" : "line",
      data: { labels: data.labels, datasets },
      options,
    });
    charts.set(canvas, grafico);
  }

  function renderHeatmap(container, data) {
    container.hidden = false;
    container.innerHTML = "";

    if (!data.x_labels || !data.x_labels.length) {
      container.innerHTML = '<div class="heatmap-empty">Sin datos para el periodo.</div>';
      return;
    }

    const columnas = data.x_labels.length;
    const grid = document.createElement("div");
    grid.className = "heatmap-grid";
    grid.style.gridTemplateColumns = `minmax(150px, 1.25fr) repeat(${columnas}, minmax(62px, 1fr))`;

    const esquina = document.createElement("div");
    esquina.className = "heatmap-label";
    grid.appendChild(esquina);
    data.x_labels.forEach((label) => {
      const celda = document.createElement("div");
      celda.className = "heatmap-col-label";
      celda.textContent = label;
      grid.appendChild(celda);
    });

    data.y_labels.forEach((label, fila) => {
      const filaLabel = document.createElement("div");
      filaLabel.className = "heatmap-label";
      filaLabel.textContent = label;
      grid.appendChild(filaLabel);

      const valores = data.matrix[fila] || [];
      const numericos = valores.filter((valor) => typeof valor === "number");
      const minimo = Math.min(...numericos);
      const maximo = Math.max(...numericos);
      const invertir = data.serie === "historico" && data.mejor && data.mejor[fila] === "menor";

      valores.forEach((valor, columna) => {
        const rango = maximo - minimo || 1;
        let intensidad = (valor - minimo) / rango;
        if (invertir) intensidad = 1 - intensidad;
        intensidad = Math.min(1, Math.max(0, intensidad));
        const fondo = mixColor("#e9f2ea", "#14532d", intensidad);
        const texto = intensidad > 0.58 ? "#f3f6ee" : "#1b261f";
        const celda = document.createElement("div");
        celda.className = "heatmap-cell";
        celda.style.backgroundColor = fondo;
        celda.style.color = texto;
        const unidad = data.units ? data.units[fila] : "";
        celda.textContent = `${valor}${unidad ? ` ${unidad}` : ""}`;
        celda.title = `${label} · ${data.x_labels[columna]}: ${valor}${unidad ? ` ${unidad}` : ""}`;
        grid.appendChild(celda);
      });
    });

    container.appendChild(grid);
    const leyenda = document.createElement("div");
    leyenda.className = "heatmap-legend";
    const etiquetas =
      data.serie === "historico" ? ["Peor", "Mejor"] : ["Menos", "Más"];
    leyenda.innerHTML = `<span>${etiquetas[0]}</span><span class="heatmap-scale"></span><span>${etiquetas[1]}</span>`;
    container.appendChild(leyenda);
  }

  function mixColor(desde, hasta, t) {
    const a = desde.replace("#", "");
    const b = hasta.replace("#", "");
    const componente = (offset) => {
      const x = Number.parseInt(a.slice(offset, offset + 2), 16);
      const y = Number.parseInt(b.slice(offset, offset + 2), 16);
      return Math.round(x + (y - x) * t)
        .toString(16)
        .padStart(2, "0");
    };
    return `#${componente(0)}${componente(2)}${componente(4)}`;
  }

  async function render(panel) {
    const serie = panel.dataset.chart;
    const surface = panel.querySelector(".chart-surface");
    const canvas = panel.querySelector("canvas");
    const heatmap = panel.querySelector(".heatmap");
    const tipoSelect = panel.querySelector(
      serie === "historico" ? "#chart-type" : "#ops-chart-type",
    );
    const metricaSelect = panel.querySelector("#chart-metric");
    const tipo = tipoSelect ? tipoSelect.value : "line";
    const metrica = serie === "historico" && metricaSelect ? metricaSelect.value : "calidad";

    setLoading(surface, true);
    try {
      const respuesta = await fetch(chartUrl(serie, tipo, metrica), {
        headers: { Accept: "application/json" },
      });
      if (!respuesta.ok) throw new Error("No se pudo cargar el gráfico");
      const data = await respuesta.json();
      const aviso = surface.querySelector(".chart-error");
      if (aviso) aviso.remove();

      if (serie === "operacion" && data.meta && data.meta.total_marcas === 0) {
        canvas.hidden = true;
        heatmap.hidden = true;
        showChartError(surface, "Sin datos para graficar en este periodo.");
        return;
      }

      if (tipo === "heatmap") {
        canvas.hidden = true;
        renderHeatmap(heatmap, data);
        return;
      }

      heatmap.hidden = true;
      canvas.hidden = false;
      drawChart(canvas, tipo, data);
    } catch (_error) {
      showChartError(surface, "No se pudo cargar el gráfico. Recarga la página.");
    } finally {
      setLoading(surface, false);
    }
  }

  function syncHidden() {
    const tipo = document.querySelector("#chart-type");
    const metrica = document.querySelector("#chart-metric");
    const ops = document.querySelector("#ops-chart-type");
    if (tipo) document.querySelector("#tipo-grafico-hidden").value = tipo.value;
    if (metrica) document.querySelector("#metrica-hidden").value = metrica.value;
    if (ops) document.querySelector("#tipo-ops-hidden").value = ops.value;
  }

  document.querySelectorAll("[data-chart]").forEach((panel) => {
    render(panel);
  });

  ["#chart-type", "#chart-metric", "#ops-chart-type"].forEach((selector) => {
    const control = document.querySelector(selector);
    if (!control) return;
    control.addEventListener("change", () => {
      syncHidden();
      const panelId = selector === "#ops-chart-type" ? "operacion" : "historico";
      const panel = document.querySelector(`[data-chart="${panelId}"]`);
      if (panel) render(panel);
    });
  });

  syncHidden();
})();
