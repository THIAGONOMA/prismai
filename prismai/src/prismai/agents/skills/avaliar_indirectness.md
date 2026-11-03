# Avaliar Indirectness (GRADE)

Avalie a aplicabilidade (indirectness) do corpo de evidência para um desfecho específico em relação à pergunta PICO do protocolo.

## Entradas
- Protocolo PICO (população, intervenção, comparação, desfecho)
- Estudos incluídos na síntese

## Saída esperada
JSON com:
- `rating`: 0 (sem downgrade), -1 (séria), -2 (muito séria)
- `justificativa`: razão da avaliação

## Critérios
1. **População**: Os participantes dos estudos diferem significativamente da população-alvo?
2. **Intervenção**: A intervenção estudada difere da intervenção de interesse?
3. **Comparador**: O comparador difere do comparador de interesse?
4. **Desfecho**: Os desfechos medidos são substitutos (surrogate) dos desfechos de interesse?

Qualquer discrepância séria justifica -1; múltiplas discrepâncias ou discrepância grave justifica -2.
