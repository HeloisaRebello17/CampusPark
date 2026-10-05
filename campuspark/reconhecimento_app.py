# reconhecimento_app.py
# Identificacao facial do CampusPark como programa independente (vira .exe com build_exe.bat).
# Faz o mesmo que "python manage.py reconhecer_rosto": abre a webcam, compara o rosto com
# os alunos cadastrados no banco e mostra nome, score e tempo gasto em milissegundos.
#
# Uso (como .exe ou como script):
#   CampusPark_Reconhecimento.exe                  -> webcam padrao
#   CampusPark_Reconhecimento.exe --camera 1       -> outra webcam
#   CampusPark_Reconhecimento.exe --imagem foto.jpg  -> reconhece a partir de um arquivo (sem webcam)
#   CampusPark_Reconhecimento.exe --teste          -> confere banco, modelos e webcam, sem abrir a tela
#
# Na janela: ESC ou Q sai | R recarrega os rostos do banco.
# O arquivo .env (DATABASE_URL etc.) precisa estar na MESMA pasta do .exe.

import argparse
import os
import sys
import time

CONGELADO = getattr(sys, "frozen", False)  # True quando rodando como .exe (PyInstaller)
PASTA_APP = os.path.dirname(sys.executable) if CONGELADO else os.path.dirname(os.path.abspath(__file__))

# Recarrega os rostos do banco de tempos em tempos: alunos cadastrados com o programa
# aberto passam a ser reconhecidos sem precisar reiniciar.
RECARGA_CACHE_SEG = 30


def preparar_django():
    os.chdir(PASTA_APP)
    if not CONGELADO and PASTA_APP not in sys.path:
        sys.path.insert(0, PASTA_APP)

    from dotenv import load_dotenv

    caminho_env = os.path.join(PASTA_APP, ".env")
    if not os.path.exists(caminho_env):
        raise FileNotFoundError(
            f"Arquivo .env nao encontrado em '{PASTA_APP}'. "
            "Copie o .env do projeto para a mesma pasta deste programa."
        )
    load_dotenv(caminho_env)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def cor_e_texto(aluno, score):
    if aluno:
        return f"{aluno.nome_completo} ({score:.2f})", (0, 200, 0)
    return f"Nao identificado ({score:.2f})", (0, 0, 220)


def modo_teste(camera_indice):
    """Diagnostico rapido: banco, modelos faciais e webcam."""
    from apps.campuspark_biometria.models import Biometria
    from integrations.camera import Camera
    from integrations.facial_recognition import FacialRecognition

    ok = True
    print(f"Pasta do programa: {PASTA_APP}")

    try:
        total = Biometria.objects.filter(ativo=True).count()
        print(f"[OK] Banco de dados acessivel. Amostras de rosto ativas: {total}")
    except Exception as exc:
        ok = False
        print(f"[FALHA] Banco de dados: {exc}")

    try:
        fr = FacialRecognition()
        print("[OK] Modelos de reconhecimento facial carregados.")
        fr.carregar_cache()
        print(f"[OK] Rostos em memoria: {len(fr._cache_alunos)}")
    except Exception as exc:
        ok = False
        print(f"[FALHA] Reconhecimento facial: {exc}")

    try:
        with Camera(camera_indice) as cam:
            cam.capturar_frame()
        print(f"[OK] Webcam {camera_indice} acessivel.")
    except Exception as exc:
        ok = False
        print(f"[FALHA] Webcam {camera_indice}: {exc}")

    print("\nTudo certo." if ok else "\nHa itens com falha (veja acima).")
    return 0 if ok else 1


def modo_imagem(caminho):
    """Reconhece a partir de um arquivo de imagem (util sem webcam)."""
    import cv2
    import numpy as np

    from integrations.facial_recognition import FacialRecognition

    if not os.path.exists(caminho):
        print(f"Arquivo nao encontrado: {caminho}")
        return 1
    # np.fromfile + imdecode: funciona com acentos no caminho (cv2.imread falha no Windows)
    frame = cv2.imdecode(np.fromfile(caminho, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        print("Nao foi possivel ler a imagem (arquivo invalido).")
        return 1

    fr = FacialRecognition()
    fr.carregar_cache()
    inicio = time.time()
    aluno, score = fr.reconhecer(frame)
    elapsed_ms = (time.time() - inicio) * 1000

    if aluno:
        print(f"Reconhecido: {aluno.nome_completo} (matricula {aluno.matricula}) | score {score:.4f} | {elapsed_ms:.0f} ms")
    else:
        print(f"Nao identificado | melhor score {score:.4f} | {elapsed_ms:.0f} ms")
    return 0


def modo_webcam(camera_indice):
    import cv2

    from integrations.camera import Camera
    from integrations.facial_recognition import FacialRecognition

    JANELA = "CampusPark - Reconhecimento facial"

    fr = FacialRecognition()
    fr.carregar_cache()
    ultima_recarga = time.time()

    if len(fr._cache_alunos) == 0:
        print("Nenhum aluno com rosto cadastrado ainda. Cadastre pela tela de cadastro de aluno.")
    print("Reconhecimento iniciado. ESC ou Q para sair | R recarrega os rostos do banco.")

    with Camera(camera_indice) as cam:
        while True:
            if time.time() - ultima_recarga >= RECARGA_CACHE_SEG:
                fr.carregar_cache()
                ultima_recarga = time.time()

            inicio = time.time()
            frame = cam.capturar_frame()
            aluno, score = fr.reconhecer(frame)
            elapsed_ms = (time.time() - inicio) * 1000

            label, cor = cor_e_texto(aluno, score)
            cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
            cv2.putText(frame, f"{elapsed_ms:.0f} ms | {len(fr._cache_alunos)} rosto(s) no banco",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow(JANELA, frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (27, ord("q"), ord("Q")):
                break
            if tecla in (ord("r"), ord("R")):
                fr.carregar_cache()
                ultima_recarga = time.time()
                print(f"Rostos recarregados: {len(fr._cache_alunos)}")
            # fechar pelo X da janela
            if cv2.getWindowProperty(JANELA, cv2.WND_PROP_VISIBLE) < 1:
                break

    cv2.destroyAllWindows()
    return 0


def main():
    parser = argparse.ArgumentParser(description="CampusPark - identificacao por reconhecimento facial.")
    parser.add_argument("--camera", type=int, default=0, help="Indice da webcam (padrao: 0).")
    parser.add_argument("--imagem", type=str, help="Reconhece a partir de um arquivo de imagem, sem webcam.")
    parser.add_argument("--teste", action="store_true", help="Verifica banco, modelos e webcam e sai.")
    args = parser.parse_args()

    preparar_django()

    if args.teste:
        return modo_teste(args.camera)
    if args.imagem:
        return modo_imagem(args.imagem)
    return modo_webcam(args.camera)


if __name__ == "__main__":
    codigo = 1
    try:
        codigo = main()
    except Exception as exc:  # mostra o erro e segura a janela aberta (no .exe ela sumiria)
        print(f"\nERRO: {exc}")
        if CONGELADO:
            input("\nPressione ENTER para sair...")
    sys.exit(codigo)
