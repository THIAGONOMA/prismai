from __future__ import annotations

from pathlib import Path

import yaml

from prismai.core.models import CasoTeste, Protocolo, Registro

_DIR = Path(__file__).parent


def carregar_protocolo() -> Protocolo:
    with open(_DIR / "protocolo.yaml") as f:
        return Protocolo(**yaml.safe_load(f))


def carregar_registros() -> list[Registro]:
    with open(_DIR / "registros.yaml") as f:
        return [Registro(**r) for r in yaml.safe_load(f)]


def carregar_casos() -> list[CasoTeste]:
    with open(_DIR / "casos.yaml") as f:
        return [CasoTeste(**c) for c in yaml.safe_load(f)]


def carregar_pares() -> dict:
    with open(_DIR / "pares.yaml") as f:
        return yaml.safe_load(f)
