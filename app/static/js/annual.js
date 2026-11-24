/* Consolidado anual: comparativas enero–enero y año–año. */
(() => {
  "use strict";

  const dataNode = document.getElementById("annual-chart-data");
  if (!dataNode || typeof Chart === "undefined") return;

  let data;
  try {
    data = JSON.parse(dataNode.textContent);
  } catch (_error) {
    return;
  }

  Chart.defaults.font.family = '"Manrope", "Segoe UI", system-ui, sans-serif';
  Chart.defaults.font.size = 10;
  Chart.defaults.color = "#52645a";
  Chart.defaults.borderColor = "rgba(23, 37, 29, 0.08)";
  Chart.defaults.animation.duration = 240;

  const palette = {
    green: "#1c5a3e",
    brass: "#855a16",
    clay: "#9a4f31",
    sage: "#8fae98",
  };

  const tooltip = {
    backgroundColor: "#0f3b2a",
    titleColor: "#f3f6ee",
    bodyColor: "#e9f2ea",
    borderColor: "#1c5a3e",
    borderWidth: 1,
    padding: 9,
    cornerRadius: 8,
    displayColors: true,
  };

  const percentageAxis = {
    beginAtZero: true,
    max: 100,
    grid: { color: "rgba(23, 37, 29, 0.07)" },
    ticks: { color: "#6c7b70", callback: (value) => `${value}%`, font: { size: 9 } },
  };

  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: "bottom",
        labels: { color: "#52645a", usePointStyle: true, boxWidth: 7, boxHeight: 7, padding: 12 },
      },
      tooltip: {
        ...tooltip,
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.parsed.y}%`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#6c7b70", font: { size: 9 } },
      },
      y: percentageAxis,
    },
  };

  const eneroCanvas = document.getElementById("chart-eneros");
  if (eneroCanvas) {
    new Chart(eneroCanvas, {
      type: "bar",
      data: {
        labels: data.eneros.labels,
        datasets: [
          {
            type: "bar",
            label: "Calidad operativa",
            data: data.eneros.calidad,
            backgroundColor: "rgba(28, 90, 62, 0.8)",
            borderColor: palette.green,
            borderWidth: 0,
            borderRadius: 4,
            maxBarThickness: 28,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Adopción NFC",
            data: data.eneros.nfc,
            borderColor: palette.brass,
            backgroundColor: palette.brass,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.25,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        ...baseOptions,
        scales: {
          x: baseOptions.scales.x,
          y: {
            beginAtZero: true,
            max: 20,
            grid: { color: "rgba(23, 37, 29, 0.07)" },
            ticks: { color: "#6c7b70", callback: (value) => `${value}%`, font: { size: 9 } },
          },
          y1: {
            position: "right",
            beginAtZero: true,
            max: 100,
            grid: { drawOnChartArea: false },
            ticks: { color: "#855a16", callback: (value) => `${value}%`, font: { size: 9 } },
          },
        },
      },
    });
  }

  const anualCanvas = document.getElementById("chart-anual");
  if (anualCanvas) {
    new Chart(anualCanvas, {
      type: "line",
      data: {
        labels: data.anual.labels,
        datasets: [
          {
            label: "Oportunidad",
            data: data.anual.oportunidad,
            borderColor: palette.green,
            backgroundColor: palette.green,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5,
          },
          {
            label: "Calidad KPI",
            data: data.anual.calidad,
            borderColor: palette.clay,
            backgroundColor: palette.clay,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5,
          },
          {
            label: "Adopción NFC",
            data: data.anual.nfc,
            borderColor: palette.brass,
            backgroundColor: palette.brass,
            borderDash: [4, 3],
            tension: 0.3,
            borderWidth: 1.8,
            pointRadius: 2.5,
            pointHoverRadius: 4,
          },
        ],
      },
      options: baseOptions,
    });
  }
})();
