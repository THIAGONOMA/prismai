# prismai

Copiloto para screening de revisão sistemática da literatura (PRISMA). A triagem é um workflow determinístico com dois nós de LLM (Triador e Auditor) e uma etapa de coleta que não chama modelo.

Extraído do projeto INF-0093 (UNICAMP). No golden set de 11 casos, a versão final acertou 11/11 em 3 execuções. Isso não é prova de que a arquitetura sozinha produz o salto: metade do ganho da v3 era regra de prompt, e a heurística de suficiência por lista de marcadores não generaliza (1/6 num held-out fora do conjunto). O julgamento de suficiência que o Triador consome é do LLM; a lista fica só como pista.

## Setup

```bash
uv sync --all-extras
cp .env.example .env  # preencher variáveis
```

## Banco de dados

O prismai usa PostgreSQL com Row-Level Security para isolamento multi-tenant.

```bash
make db-up    # sobe Postgres via docker-compose e roda migrações
make db-down  # derruba Postgres e apaga volumes
make migrate  # apenas alembic upgrade head
```

A aplicação conecta via role `prismai_app` (NOSUPERUSER NOBYPASSRLS), de modo que as
policies de RLS são sempre aplicadas. Migrações rodam via role `postgres` (owner).

## Testes

```bash
make test   # unitários + integração + contrato (sem rede, sem chave)
make eval   # avaliação com LLM real (requer OPENAI_API_KEY)
make lint   # ruff check + format
```

Os testes marcados com `@pytest.mark.postgres` requerem `DATABASE_URL_TEST` no ambiente.
Os demais rodam inteiramente em memória.

## API

```bash
make api    # sobe em http://localhost:8000
```

### Autenticação

```bash
# Registrar org + usuário
curl -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"org_name": "minha-org", "username": "usuario", "password": "senha"}'

# Obter token
curl -X POST http://localhost:8000/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username": "usuario", "password": "senha"}'
```

## Busca bibliográfica

O prismai busca registros diretamente de fontes abertas via API:

```bash
# Buscar no OpenAlex
curl -X POST http://localhost:8000/v1/reviews/minha-review/search \
  -H 'Content-Type: application/json' \
  -d '{"source": "openalex", "query": "PRISMA systematic review", "max_results": 100}'

# Buscar no Crossref
curl -X POST http://localhost:8000/v1/reviews/minha-review/search \
  -H 'Content-Type: application/json' \
  -d '{"source": "crossref", "query": "PRISMA systematic review", "max_results": 100}'
```

Registros duplicados (mesmo DOI ou título similar) são automaticamente ignorados.

Para usar a cota completa do OpenAlex (100k créditos/dia), configure `PRISMAI_OPENALEX_API_KEY`.

## Importação de arquivo

Upload de CSV, RIS ou BibTeX com detecção automática de formato e mapeamento de colunas:

```bash
curl -X POST http://localhost:8000/v1/reviews/minha-review/import \
  -F 'file=@referencias.ris'
```

Formatos suportados: `.csv`, `.tsv`, `.ris`, `.bib`/`.bibtex`.
Colunas CSV reconhecidas automaticamente: `title`, `abstract`, `doi`, `authors`, `year` (e variantes em português).

## Dupla triagem (M3)

O prismai suporta screening dual com dois modelos independentes (ex.: GPT-4o-mini + Claude 3.5 Sonnet).
Quando as decisões divergem, um conflito é criado e enfileirado para revisão humana, ordenado por gravidade.

```bash
# Iniciar dual screening
curl -X POST http://localhost:8000/v1/reviews/minha-review/screening/run \
  -H 'Content-Type: application/json' \
  -d '{"mode": "dual", "model": "gpt-4o-mini", "model_b": "claude-3-5-sonnet-20241022"}'

# Listar conflitos pendentes (ordenados por disagreement_score)
curl http://localhost:8000/v1/reviews/minha-review/conflicts?status=pending

# Resolver um conflito
curl -X POST http://localhost:8000/v1/reviews/minha-review/conflicts/r1/resolve \
  -H 'Content-Type: application/json' \
  -d '{"decision": "include", "note": "Evidência suficiente no abstract"}'

# Ver métricas de concordância (Cohen's kappa)
curl http://localhost:8000/v1/reviews/minha-review/agreement
```

A parada estatística monitora a taxa de concordância via Wilson score interval e encerra
automaticamente quando o limite inferior atinge o threshold configurado (`PRISMAI_STOPPING_THRESHOLD`).

## Recuperação de full-text (M4)

Após o screening, registros incluídos podem ter seus PDFs recuperados automaticamente
via cascata Unpaywall → PMC → arXiv → DOI resolver, com extração de layout via GROBID.

```bash
# Subir GROBID
make grobid

# Disparar recuperação de full-text para uma revisão
curl -X POST http://localhost:8000/v1/reviews/minha-review/fulltext/fetch

# Listar documentos recuperados
curl http://localhost:8000/v1/reviews/minha-review/documents

# Upload manual de PDF
curl -X POST http://localhost:8000/v1/reviews/minha-review/documents/rec-1/upload \
  -F 'file=@artigo.pdf'
```

PDFs com OCR insuficiente (abaixo de `PRISMAI_OCR_CONFIDENCE_THRESHOLD`) são marcados
como `requires_manual_transcription` e não avançam para elegibilidade.

## Elegibilidade por full-text (M4)

O grafo de elegibilidade avalia documentos extraídos contra os critérios do protocolo
usando fan-out por critério, consolidação booleana determinística e auditoria de citação.

```bash
# Disparar avaliação de elegibilidade
curl -X POST http://localhost:8000/v1/reviews/minha-review/eligibility/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Listar decisões de elegibilidade
curl http://localhost:8000/v1/reviews/minha-review/eligibility
```

Cada decisão inclui evidências ancoradas (página, offset) verificadas pelo auditor de citação.

## Extração de dados estruturados (M5)

Após a elegibilidade, documentos incluídos passam por extração automática de dados seguindo
um schema configurável (padrão Cochrane). O grafo usa fan-out por bloco temático (população,
intervenção, comparador, desfechos, estatísticas, metadados), verificação numérica determinística
e auditoria de citação.

```bash
# Configurar schema customizado (opcional)
curl -X POST http://localhost:8000/v1/reviews/minha-review/extraction-schema \
  -H 'Content-Type: application/json' \
  -d '{"schema_data": {"version": "custom-v1", "fields": [...]}}'

# Disparar extração
curl -X POST http://localhost:8000/v1/reviews/minha-review/extraction/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Listar extrações
curl http://localhost:8000/v1/reviews/minha-review/extraction

# Detalhe de uma extração
curl http://localhost:8000/v1/reviews/minha-review/extraction/rec-1
```

Células com inconsistências numéricas (ex.: n_total ≠ n_intervencao + n_controle) são
automaticamente flagueadas e marcadas para confirmação humana.

## Risco de viés — RoB 2 (M5)

Avaliação de risco de viés usando o instrumento RoB 2 (Cochrane), com fan-out por domínio
(randomização, desvios, dados faltantes, mensuração, seleção de resultado), julgamento
determinístico e auditoria de citação.

```bash
# Disparar avaliação de RoB
curl -X POST http://localhost:8000/v1/reviews/minha-review/rob/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Listar avaliações de RoB
curl http://localhost:8000/v1/reviews/minha-review/rob
```

## Worker

O worker SAQ processa jobs de screening, full-text, elegibilidade, extração, RoB, síntese e GRADE em background:

```bash
make worker  # inicia o worker SAQ
```

## Síntese e meta-análise (M6)

Após RoB, o prismai executa síntese quantitativa (meta-análise) por desfecho configurado.
Usa DerSimonian-Laird para efeitos aleatórios, calcula I², Q, intervalo de predição e teste de Egger.

```bash
# Configurar desfechos para síntese
curl -X POST http://localhost:8000/v1/reviews/minha-review/synthesis-config \
  -H 'Content-Type: application/json' \
  -d '{"config": {"version": "v1", "outcomes": [{"key": "pain", "nome": "Dor", "tipo": "continuous", "measure": "smd"}]}}'

# Disparar síntese
curl -X POST http://localhost:8000/v1/reviews/minha-review/synthesis/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Listar sínteses
curl http://localhost:8000/v1/reviews/minha-review/synthesis

# Forest plot (JSON)
curl http://localhost:8000/v1/reviews/minha-review/synthesis/pain/forest

# Funnel plot (JSON)
curl http://localhost:8000/v1/reviews/minha-review/synthesis/pain/funnel
```

Para renderizar plots em PNG, instale `pip install prismai[plots]`.

## Certeza da evidência — GRADE (M6)

Avaliação automatizada da certeza da evidência usando o framework GRADE.
Quatro domínios são determinísticos (risco de viés, inconsistência, imprecisão, viés de publicação)
e um usa LLM (indirectness).

```bash
# Disparar avaliação GRADE
curl -X POST http://localhost:8000/v1/reviews/minha-review/grade/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Tabela Summary of Findings
curl http://localhost:8000/v1/reviews/minha-review/grade/sof
```

## Relato PRISMA 2020 (M7)

Geração automatizada do relatório PRISMA 2020 com diagrama de fluxo, checklist de 27 itens
e seções de Métodos e Resultados redigidas por LLM com auditoria numérica.

```bash
# Diagrama de fluxo PRISMA (JSON)
curl http://localhost:8000/v1/reviews/minha-review/prisma-flow

# Diagrama SVG
curl http://localhost:8000/v1/reviews/minha-review/prisma-flow.svg > prisma.svg

# Checklist PRISMA 2020
curl http://localhost:8000/v1/reviews/minha-review/checklist

# Gerar relatório completo
curl -X POST http://localhost:8000/v1/reviews/minha-review/report/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Obter relatório (Markdown, HTML ou DOCX)
curl http://localhost:8000/v1/reviews/minha-review/report.md
curl http://localhost:8000/v1/reviews/minha-review/report.html
curl http://localhost:8000/v1/reviews/minha-review/report.docx -o report.docx

# Aprovar relatório
curl -X POST http://localhost:8000/v1/reviews/minha-review/report/approve
```

O auditor numérico verifica que nenhum número inventado pelo LLM aparece no texto final.
Números ausentes nos dados são removidos e flagueados automaticamente.

## Exportação (M7)

Pacote de reprodutibilidade com todos os dados, decisões, traces e artefatos:

```bash
curl http://localhost:8000/v1/reviews/minha-review/export -o pacote.zip
```

O ZIP contém: protocol.json, records.json, decisions.json, eligibility.json, extractions.json,
rob.json, syntheses.json, grade.json, checklist.json, prisma_flow.svg, report.md, report.html.

Para DOCX, instale `pip install prismai[report]`.

## Revisão Viva (M8)

O prismai suporta revisões vivas (living systematic reviews) com busca incremental,
triagem automática de novos registros e detecção determinística de impacto.

```bash
# Ativar revisão viva com agendamento semanal
curl -X POST http://localhost:8000/v1/reviews/minha-review/living/enable \
  -H 'Content-Type: application/json' \
  -d '{"cron": "0 3 * * 1"}'

# Disparar atualização manual
curl -X POST http://localhost:8000/v1/reviews/minha-review/living/run \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini"}'

# Ver status e histórico de atualizações
curl http://localhost:8000/v1/reviews/minha-review/living/status
curl http://localhost:8000/v1/reviews/minha-review/living/updates

# Desativar revisão viva
curl -X POST http://localhost:8000/v1/reviews/minha-review/living/disable
```

### Detector de Impacto

O detector de impacto compara resultados de síntese antes e depois de novos estudos e identifica:
- **Mudança de direção**: sinal do efeito pooled inverteu
- **Mudança de significância**: p-valor cruzou 0.05
- **Mudança de heterogeneidade**: I² variou mais de 25 pontos percentuais
- **Mudança de certeza**: nível GRADE subiu ou desceu
- **Novo desfecho**: outcome apareceu com novos estudos

## Arquitetura

```
Client → API (FastAPI) → SAQ Queue (Postgres) → Worker → LLM
                ↕                                   ↕
            Postgres (RLS por org_id)           GROBID (PDF)
                ↑
   OpenAlex / Crossref / CSV / RIS / BibTeX
   Unpaywall / PMC / arXiv (PDFs)
```
