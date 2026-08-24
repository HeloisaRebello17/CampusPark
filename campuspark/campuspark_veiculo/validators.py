# validators.py
# Regras de negócio para veículos.
def validar_placa_unica(placa, carros_existentes):
    if placa in carros_existentes:
        raise ValueError("Placa já cadastrada.")
