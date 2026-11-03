import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for proportion k/n at confidence z."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / d
    margem = z / d * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (round(max(0.0, centro - margem), 4), round(min(1.0, centro + margem), 4))
