"""Synthesis config loader — no default, explicit config required."""
from __future__ import annotations

from prismai.core.models import SynthesisConfig


def carregar_synthesis_config(raw: dict | None) -> SynthesisConfig | None:
    """Validate raw dict into SynthesisConfig, or return None if not configured."""
    if raw is None:
        return None
    return SynthesisConfig.model_validate(raw)
