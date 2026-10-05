// ui.js: pequenas interações visuais das telas (sem chamadas a backend)

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

  // Placa do veículo: maiúsculas, só letras e números (sem espaço/traço/símbolo)
  document.querySelectorAll("[data-placa-mask]").forEach((input) => {
    input.addEventListener("input", () => {
      input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
    });
  });

  // Aceita só dígitos em campos marcados (ex.: RA no login)
  document.querySelectorAll("[data-digits-only]").forEach((input) => {
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "");
    });
  });

  // Máscara de CPF: 000.000.000-00, formatada enquanto digita
  document.querySelectorAll("[data-cpf-mask]").forEach((input) => {
    input.addEventListener("input", () => {
      const digitos = input.value.replace(/\D/g, "").slice(0, 11);
      let formatado = digitos;
      if (digitos.length > 9) {
        formatado = `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`;
      } else if (digitos.length > 6) {
        formatado = `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6)}`;
      } else if (digitos.length > 3) {
        formatado = `${digitos.slice(0, 3)}.${digitos.slice(3)}`;
      }
      input.value = formatado;
    });
    input.dispatchEvent(new Event("input"));
  });

  // Menu do sidebar em telas pequenas
  document.querySelectorAll("[data-sidebar-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelector(".sidebar")?.classList.toggle("is-open");
    });
  });
});
