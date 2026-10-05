// captura_facial.js
// Captura as fotos do rosto na tela de cadastro do aluno (getUserMedia) e as coloca
// no <input type="file" name="fotos_rosto"> do formulario, que segue no mesmo POST.
// A deteccao do rosto e feita no servidor (BiometriaService); aqui so capturamos.
//
// A camera so funciona em contexto seguro: https:// ou http://localhost.

document.addEventListener("DOMContentLoaded", () => {
  const raiz = document.querySelector("[data-face-capture]");
  if (!raiz) return;

  const form = raiz.closest("form");
  const alvo = parseInt(raiz.dataset.alvo, 10) || 5;
  const intervaloMs = 500;

  const video = raiz.querySelector("[data-face-video]");
  const placeholder = raiz.querySelector("[data-face-placeholder]");
  const palco = raiz.querySelector(".face-capture-stage");
  const miniaturas = raiz.querySelector("[data-face-thumbs]");
  const status = raiz.querySelector("[data-face-status]");
  const btnIniciar = raiz.querySelector("[data-face-start]");
  const btnCapturar = raiz.querySelector("[data-face-shoot]");
  const inputArquivos = raiz.querySelector("[data-face-files]");
  const inputUpload = raiz.querySelector("[data-face-upload]");

  let stream = null;
  let capturando = false;

  function mensagem(texto, tipo) {
    status.textContent = texto;
    status.classList.toggle("is-ok", tipo === "ok");
    status.classList.toggle("is-erro", tipo === "erro");
  }

  function pararCamera() {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    video.srcObject = null;
    video.hidden = true;
    placeholder.hidden = false;
  }

  function definirArquivos(arquivos) {
    const dt = new DataTransfer();
    arquivos.forEach((a) => dt.items.add(a));
    inputArquivos.files = dt.files;

    miniaturas.innerHTML = "";
    arquivos.forEach((arq) => {
      const img = document.createElement("img");
      img.alt = "Foto do rosto";
      img.src = URL.createObjectURL(arq);
      miniaturas.appendChild(img);
    });
  }

  async function iniciarCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      mensagem(
        "Seu navegador não liberou a câmera. Acesse por https:// ou http://localhost e use um navegador atualizado.",
        "erro"
      );
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
    } catch (e) {
      const negada = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
      mensagem(
        negada
          ? "Permissão da câmera negada. Libere o acesso à câmera no navegador e tente de novo."
          : "Não foi possível acessar a câmera. Verifique se ela está conectada e livre.",
        "erro"
      );
      return;
    }
    video.srcObject = stream;
    video.hidden = false;
    placeholder.hidden = true;
    btnIniciar.hidden = true;
    btnCapturar.hidden = false;
    mensagem("Câmera ligada. Enquadre seu rosto e clique em tirar as fotos.");
  }

  function esperar(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function frameParaArquivo(indice) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    // Sem espelhar: o modelo recebe a imagem real (so o preview e espelhado via CSS).
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => resolve(new File([blob], `rosto_${indice + 1}.jpg`, { type: "image/jpeg" })),
        "image/jpeg",
        0.92
      );
    });
  }

  async function capturar() {
    if (capturando || !stream) return;
    if (!video.videoWidth) {
      mensagem("A câmera ainda está iniciando. Aguarde um instante.", "erro");
      return;
    }
    capturando = true;
    btnCapturar.disabled = true;
    palco.classList.add("is-shooting");
    definirArquivos([]);

    const arquivos = [];
    for (let i = 0; i < alvo; i++) {
      mensagem(`Fique parado, olhando para a câmera... foto ${i + 1} de ${alvo}`);
      arquivos.push(await frameParaArquivo(i));
      if (i < alvo - 1) await esperar(intervaloMs);
    }

    definirArquivos(arquivos);
    palco.classList.remove("is-shooting");
    btnCapturar.disabled = false;
    btnCapturar.textContent = "Refazer fotos";
    capturando = false;
    mensagem(`${arquivos.length} fotos capturadas.`, "ok");
  }

  btnIniciar.addEventListener("click", iniciarCamera);
  btnCapturar.addEventListener("click", capturar);

  if (inputUpload) {
    inputUpload.addEventListener("change", () => {
      const arquivos = Array.from(inputUpload.files || []);
      definirArquivos(arquivos);
      mensagem(
        arquivos.length ? `${arquivos.length} foto(s) selecionada(s).` : "Nenhuma foto selecionada.",
        arquivos.length ? "ok" : undefined
      );
    });
  }

  // Impede enviar o cadastro sem as fotos (o servidor valida de novo).
  form.addEventListener("submit", (ev) => {
    if (capturando) {
      ev.preventDefault();
      return;
    }
    if (!inputArquivos.files || inputArquivos.files.length === 0) {
      ev.preventDefault();
      mensagem("Tire as fotos do rosto antes de criar a conta.", "erro");
      raiz.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  window.addEventListener("pagehide", pararCamera);
});
