/* Shaula_efc · interacciones base (sin dependencias) */
(() => {
  "use strict";

  // Mostrar / ocultar contraseña ------------------------------------------
  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    const input = document.getElementById(button.dataset.togglePassword);
    if (!input) return;

    button.addEventListener("click", () => {
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.classList.toggle("is-visible", visible);
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute(
        "aria-label",
        visible ? "Ocultar contraseña" : "Mostrar contraseña"
      );
      input.focus({ preventScroll: true });
    });
  });

  // Cerrar avisos flash -----------------------------------------------------
  document.querySelectorAll("[data-dismiss]").forEach((button) => {
    button.addEventListener("click", () => {
      const flash = button.closest(".flash");
      if (!flash) return;
      flash.style.transition = "opacity 160ms ease, transform 160ms ease";
      flash.style.opacity = "0";
      flash.style.transform = "translateY(-4px)";
      window.setTimeout(() => flash.remove(), 180);
    });
  });

  // Estado de carga al enviar formularios ----------------------------------
  document.querySelectorAll("form[data-loading]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-submit]");
      if (!button) return;
      button.classList.add("is-loading");
      button.setAttribute("aria-busy", "true");
    });
  });

  // Menú lateral en móviles -------------------------------------------------
  const sidebar = document.getElementById("sidebar");
  const overlay = document.querySelector("[data-sidebar-overlay]");
  const openButton = document.querySelector("[data-sidebar-toggle]");
  const closeButton = document.querySelector("[data-sidebar-close]");

  if (sidebar && overlay) {
    const openNav = () => {
      sidebar.classList.add("is-open");
      overlay.hidden = false;
      document.body.classList.add("nav-open");
      window.requestAnimationFrame(() => overlay.classList.add("is-visible"));
      openButton?.setAttribute("aria-expanded", "true");
      closeButton?.focus({ preventScroll: true });
    };

    const closeNav = () => {
      sidebar.classList.remove("is-open");
      overlay.classList.remove("is-visible");
      document.body.classList.remove("nav-open");
      openButton?.setAttribute("aria-expanded", "false");
      window.setTimeout(() => {
        overlay.hidden = true;
      }, 200);
      openButton?.focus({ preventScroll: true });
    };

    openButton?.addEventListener("click", openNav);
    closeButton?.addEventListener("click", closeNav);
    overlay.addEventListener("click", closeNav);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
        closeNav();
      }
    });
  }
})();
