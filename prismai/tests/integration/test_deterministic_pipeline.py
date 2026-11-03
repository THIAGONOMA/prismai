"""Pipeline determinístico: triador_fake → auditor_deterministico → avaliar.

Prova que o núcleo determinístico produz resultados corretos para os 12 registros
do golden set, sem rede e sem API key.
"""
from __future__ import annotations

import pytest

from prismai.agents.deterministic_auditor import auditor_deterministico
from prismai.checks.screening import avaliar
from prismai.core.models import ScreeningResult

# IDs dos casos com verificação automática (exclui T09 = manual)
CASOS_AUTO = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T10", "T11", "T12", "T15"]
CASO_MANUAL = "T09"


class TestDeterministicPipeline:
    """Testa cada caso do golden set pelo caminho determinístico."""

    def _run_caso(self, caso, registro, triador_output):
        resultado = auditor_deterministico(triador_output, registro)
        assert isinstance(resultado, ScreeningResult)
        return avaliar(caso, resultado, registro)

    @pytest.mark.parametrize("caso_id", CASOS_AUTO)
    def test_caso_auto_aprovado(self, caso_id, casos_map, registros_map, triador_outputs):
        caso = casos_map[caso_id]
        registro = registros_map[caso["registro_id"]]
        triador_output = triador_outputs[caso["registro_id"]]

        avaliacao = self._run_caso(caso, registro, triador_output)
        assert avaliacao["aprovado"] is True, (
            f"{caso_id} (registro {caso['registro_id']}): esperado aprovado=True, "
            f"obteve {avaliacao}"
        )

    def test_caso_manual_retorna_none(self, casos_map, registros_map, triador_outputs):
        caso = casos_map[CASO_MANUAL]
        registro = registros_map[caso["registro_id"]]
        triador_output = triador_outputs[caso["registro_id"]]

        avaliacao = self._run_caso(caso, registro, triador_output)
        assert avaliacao["aprovado"] is None, (
            f"T09 (manual): esperado aprovado=None, obteve {avaliacao}"
        )

    def test_decisao_correta_todos_auto(self, casos_map, registros_map, triador_outputs):
        """Verifica que a decisão bate com o esperado em todos os casos auto."""
        for caso_id in CASOS_AUTO:
            caso = casos_map[caso_id]
            reg = registros_map[caso["registro_id"]]
            tri = triador_outputs[caso["registro_id"]]
            resultado = auditor_deterministico(tri, reg)

            aceitos = list(caso.get("aceitos") or [])
            if caso["esperado"] not in aceitos:
                aceitos.append(caso["esperado"])
            assert resultado.decision in aceitos, (
                f"{caso_id}: decisão '{resultado.decision}' não está em {aceitos}"
            )

    def test_include_cases_tem_evidencia(self, casos_map, registros_map, triador_outputs):
        """Casos include devem retornar evidências validadas (não vazia)."""
        include_ids = [c for c in CASOS_AUTO if casos_map[c].get("esperado") == "include"]
        for caso_id in include_ids:
            caso = casos_map[caso_id]
            reg = registros_map[caso["registro_id"]]
            tri = triador_outputs[caso["registro_id"]]
            resultado = auditor_deterministico(tri, reg)

            assert len(resultado.evidence) > 0, (
                f"{caso_id}: include sem evidências validadas"
            )

    def test_uncertain_tem_confidence_baixa(self, casos_map, registros_map, triador_outputs):
        """Casos uncertain devem ter confidence low."""
        uncertain_ids = [c for c in CASOS_AUTO if casos_map[c].get("esperado") == "uncertain"]
        for caso_id in uncertain_ids:
            caso = casos_map[caso_id]
            reg = registros_map[caso["registro_id"]]
            tri = triador_outputs[caso["registro_id"]]
            resultado = auditor_deterministico(tri, reg)

            assert resultado.confidence == "low", (
                f"{caso_id}: uncertain com confidence '{resultado.confidence}', esperado 'low'"
            )

    def test_todos_12_registros_processados(self, casos_map, registros_map, triador_outputs):
        """Garante que nenhum registro ficou de fora."""
        todos = list(CASOS_AUTO) + [CASO_MANUAL]
        assert len(todos) == 13  # 12 auto + 1 manual = 13 casos no golden set

        for caso_id in todos:
            caso = casos_map[caso_id]
            reg = registros_map[caso["registro_id"]]
            tri = triador_outputs[caso["registro_id"]]
            resultado = auditor_deterministico(tri, reg)
            assert isinstance(resultado, ScreeningResult)
