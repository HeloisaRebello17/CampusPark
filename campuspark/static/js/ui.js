// ui.js — pequenas interações visuais das telas (sem chamadas a backend)

document.addEventListener("DOMContentLoaded", () => {
  // Seletor de tipo de veículo (Automóvel / Motocicleta)
  document.querySelectorAll("[data-option-group]").forEach((group) => {
    const options = group.querySelectorAll("[data-option]");
    options.forEach((option) => {
      option.addEventListener("click", () => {
        options.forEach((o) => o.classList.remove("is-selected"));
        option.classList.add("is-selected");
        const input = option.querySelector("input[type=radio]");
        if (input) input.checked = true;
      });
    });
  });

  // Mostrar/ocultar senha na tela de login
  document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
    const input = document.getElementById(btn.dataset.passwordToggle);
    const eyeIcon = btn.querySelector(".icon-eye");
    const eyeOffIcon = btn.querySelector(".icon-eye-off");
    if (!input) return;
    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      eyeIcon.hidden = !showing;
      eyeOffIcon.hidden = showing;
      btn.setAttribute("aria-label", showing ? "Mostrar senha" : "Ocultar senha");
    });
  });

  // Upload de foto de perfil: mostra pré-visualização local
  document.querySelectorAll("[data-photo-input]").forEach((input) => {
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      const preview = document.querySelector(input.dataset.photoInput);
      if (file && preview) {
        preview.style.backgroundImage = `url(${URL.createObjectURL(file)})`;
        preview.classList.add("has-photo");
      }
    });
  });

  // Menu do sidebar em telas pequenas
  document.querySelectorAll("[data-sidebar-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelector(".sidebar")?.classList.toggle("is-open");
    });
  });
});
