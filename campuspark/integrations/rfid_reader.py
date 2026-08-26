class RFIDReader:
    """No MVP a leitura é simulada — troca-se por SDK real do leitor físico depois."""

    def ler_tag(self) -> str:
        return input("Simulação: digite a TAG lida pelo leitor -> ").strip()