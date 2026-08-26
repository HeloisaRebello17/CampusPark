def somente_numeros(texto: str) -> str:
    """Remove tudo que não for dígito — útil para normalizar CPF/placa antes de salvar."""
    return "".join(c for c in texto if c.isdigit())