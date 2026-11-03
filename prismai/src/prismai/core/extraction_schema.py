"""Default extraction schema (Cochrane-style) and loader."""
from __future__ import annotations

from prismai.core.models import ExtractionFieldSpec, ExtractionSchema


def _f(name: str, block: str, tipo: str, descricao: str, **kw) -> ExtractionFieldSpec:
    return ExtractionFieldSpec(name=name, block=block, tipo=tipo, descricao=descricao, **kw)


COCHRANE_DEFAULT = ExtractionSchema(
    version="cochrane-default-v2",
    fields=[
        # populacao
        _f("desenho_estudo", "populacao", "text", "Desenho do estudo (ex.: RCT, coorte)"),
        _f("n_total", "populacao", "integer", "Número total de participantes"),
        _f("criterios_elegibilidade", "populacao", "text", "Critérios de elegibilidade do estudo"),
        _f("pais", "populacao", "text", "País onde o estudo foi conduzido"),
        _f("faixa_etaria", "populacao", "text", "Faixa etária dos participantes"),
        # intervencao
        _f("descricao_intervencao", "intervencao", "text", "Descrição da intervenção"),
        _f("dose", "intervencao", "text", "Dose da intervenção"),
        _f("duracao", "intervencao", "text", "Duração da intervenção"),
        _f("via_administracao", "intervencao", "text", "Via de administração"),
        # comparador
        _f("descricao_comparador", "comparador", "text", "Descrição do comparador"),
        _f("tipo_controle", "comparador", "text", "Tipo de controle (placebo, ativo, etc.)"),
        # desfechos
        _f("desfecho_primario", "desfechos", "text", "Desfecho primário"),
        _f("desfechos_secundarios", "desfechos", "list", "Desfechos secundários"),
        _f("instrumento_medida", "desfechos", "text", "Instrumento de medida utilizado"),
        _f("tempo_seguimento", "desfechos", "text", "Tempo de seguimento"),
        # estatisticas
        _f("n_intervencao", "estatisticas", "integer", "N do grupo intervenção"),
        _f("n_controle", "estatisticas", "integer", "N do grupo controle"),
        _f("media_intervencao", "estatisticas", "number", "Média do grupo intervenção"),
        _f("dp_intervencao", "estatisticas", "number", "Desvio-padrão do grupo intervenção"),
        _f("media_controle", "estatisticas", "number", "Média do grupo controle"),
        _f("dp_controle", "estatisticas", "number", "Desvio-padrão do grupo controle"),
        _f("valor_p", "estatisticas", "number", "Valor-p"),
        _f("ic_95", "estatisticas", "text", "Intervalo de confiança 95%"),
        _f("eventos_intervencao", "estatisticas", "integer", "Número de eventos no grupo intervenção"),
        _f("eventos_controle", "estatisticas", "integer", "Número de eventos no grupo controle"),
        # metadados
        _f("financiamento", "metadados", "text", "Fonte de financiamento"),
        _f("conflitos_interesse", "metadados", "text", "Declaração de conflitos de interesse"),
        _f("registro_protocolo", "metadados", "text", "Registro de protocolo (ex.: ClinicalTrials.gov)"),
        _f("ano_publicacao", "metadados", "integer", "Ano de publicação"),
    ],
)


def carregar_schema(raw: dict | None) -> ExtractionSchema:
    """Validate raw dict into ExtractionSchema, or return COCHRANE_DEFAULT."""
    if raw is None:
        return COCHRANE_DEFAULT
    return ExtractionSchema.model_validate(raw)
