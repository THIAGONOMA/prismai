from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class Resposta(BaseModel, Generic[T]):
    resultado: T  # type: ignore[valid-type]
    degradado: bool = False
    motivo_degradacao: str | None = None
    alertas: list[str] = Field(default_factory=list)

    def apresentar(self) -> str:
        cabecalho = f"[RESPOSTA DEGRADADA - {self.motivo_degradacao}]\n" if self.degradado else ""
        return cabecalho + str(self.resultado)
