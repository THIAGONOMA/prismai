from prismai.core.errors import TipoErro, classificar_erro, dano_ponderado


class TestClassificarErro:
    def test_approved_returns_none(self):
        assert classificar_erro({"aprovado": True}) is None

    def test_none_approved_returns_none(self):
        assert classificar_erro({"aprovado": None}) is None

    def test_falso_negativo(self):
        r = {
            "aprovado": False,
            "decisao_correta": False,
            "esperado": "include",
            "decision": "exclude",
        }
        erros = classificar_erro(r)
        assert TipoErro.FALSO_NEGATIVO in erros

    def test_falso_positivo(self):
        r = {
            "aprovado": False,
            "decisao_correta": False,
            "esperado": "exclude",
            "decision": "include",
        }
        erros = classificar_erro(r)
        assert TipoErro.FALSO_POSITIVO in erros

    def test_evidencia_fabricada(self):
        r = {"aprovado": False, "evidencia_fiel": 0.5}
        erros = classificar_erro(r)
        assert TipoErro.EVIDENCIA_FABRICADA in erros


class TestDanoPonderado:
    def test_all_approved(self):
        resultados = [{"aprovado": True}, {"aprovado": True}]
        r = dano_ponderado(resultados)
        assert r["qualidade_ponderada"] == 1.0

    def test_one_falso_negativo(self):
        resultados = [
            {"aprovado": True},
            {
                "aprovado": False,
                "decisao_correta": False,
                "esperado": "include",
                "decision": "exclude",
            },
        ]
        r = dano_ponderado(resultados)
        assert r["qualidade_ponderada"] < 1.0
        assert r["dano_total"] == 5
        assert r["dano_maximo"] == 10
        assert r["qualidade_ponderada"] == 0.5
