alto = 100
baixo = 0


meio = (baixo + alto) // 2  # Divisão inteira para garantir que 'meio' seja um número inteiro
chute = list[meio]

# Verifica se 'meio' é um número inteiro
if isinstance(meio, int):
    print(f"Meio é um número inteiro: {meio}")
else:
    print(f"Meio não é um número inteiro: {meio}")