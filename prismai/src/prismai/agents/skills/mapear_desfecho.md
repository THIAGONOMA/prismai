# Mapear Desfecho

Dado um desfecho configurado no protocolo de síntese, identifique quais estudos (extrações) medem esse desfecho.

## Entradas
- Nome e sinônimos do desfecho configurado
- Lista de extrações com campos: desfecho_primario, desfechos_secundarios, instrumento_medida

## Saída esperada
JSON array com objetos contendo:
- `record_id`: identificador do estudo
- `incluido`: booleano indicando se o estudo mede este desfecho
- `motivo`: razão caso excluído

## Regras
1. Use correspondência semântica, não apenas exata
2. Considere sinônimos fornecidos na configuração
3. Se o instrumento de medida é incompatível com a medida configurada, exclua
4. Estudos sem dados numéricos suficientes devem ser incluídos (serão filtrados na etapa de cálculo)
