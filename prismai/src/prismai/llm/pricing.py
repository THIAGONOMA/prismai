PRECO_POR_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
}


def estimar_custo(modelo: str, tokens_entrada: int, tokens_saida: int) -> float:
    precos = PRECO_POR_1K_TOKENS.get(modelo, PRECO_POR_1K_TOKENS["gpt-4o-mini"])
    return (tokens_entrada / 1000) * precos["input"] + (tokens_saida / 1000) * precos["output"]
