# Simulação da cancela física de entrada/saída (ADR-004: hardware simulado em
# integrations/, trocado pelo controlador real da cancela numa fase futura).

class Cancela:
    """No MVP, 'abrir' a cancela é só um registro simulado no console."""

    def abrir(self, motivo: str = "") -> None:
        print(f"[CANCELA] Abrindo cancela. {motivo}".strip())

    def fechar(self) -> None:
        print("[CANCELA] Fechando cancela.")