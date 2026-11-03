# PrismAI

Copiloto de revisão sistemática no fluxo PRISMA 2020. Cada decisão automática fica ligada a um trecho da fonte, e o ponto de risco para à espera de uma pessoa.

Autor: Thiago Nobre Mascarenhas. Origem: INF-0093, Instituto de Computação, UNICAMP. Licença MIT, no pacote [`prismai/LICENSE`](prismai/LICENSE).

## O que há aqui

| Pasta | Papel |
|---|---|
| [`prismai/`](prismai/) | API, fila, banco, agentes e testes. O uso detalhado está no [README do pacote](prismai/README.md). |
| [`prismai-web/`](prismai-web/) | Interface: login, lista de revisões e as abas de protocolo, triagem, full-text, extração, síntese, GRADE, relatório e revisão viva. |
| [`planoMaster.md`](planoMaster.md) | Desenho do produto, do protocolo ao relato. |

## O que o fluxo cobre

1. Protocolo com pergunta e PICO, gravado por revisão.
2. Busca em OpenAlex e Crossref, ou importação de CSV, RIS e BibTeX, com deduplicação.
3. Triagem de título e abstract, com opção de dois triadores, conflito e kappa.
4. Recuperação de PDF (Unpaywall, PMC, arXiv, DOI) e elegibilidade no texto completo.
5. Extração no formulário Cochrane, risco de viés RoB 2, síntese e GRADE.
6. Relato com fluxo, checklist e exportação.
7. Revisão viva, com busca incremental e detector de impacto.

A chave de modelo fica fora do repositório. Sem ela, a API, o banco e os testes sem rede sobem. A triagem com modelo de linguagem usa a chave que você colocar no ambiente local.

## Subir em um comando

Na pasta `prismai`, com Docker:

```bash
docker compose up --build
```

A API fica em `http://localhost:8000` e a interface em `http://localhost:3000`. O Postgres e o GROBID sobem no mesmo compose. As senhas desse banco são as de desenvolvimento local; não valem para um ambiente exposto.

## Subir sem Docker

```bash
cd prismai
uv sync --all-extras
cp .env.example .env
make db-up
make api
```

Em outro terminal, o worker e a interface:

```bash
cd prismai && make worker
cd prismai-web && npm install && npm run dev
```

O arquivo `.env` não é versionado. O exemplo [`.env.example`](prismai/.env.example) traz os nomes das variáveis, com valores de marcação no lugar das chaves. Troque `PRISMAI_JWT_SECRET` antes de qualquer uso que não seja a sua máquina.

A primeira conta sai pela API:

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"org_name": "minha-org", "username": "usuario", "password": "escolha-uma-senha"}'
```

A interface só faz login. O registro é esse pedido.

## Testes

```bash
cd prismai
make test
```

A avaliação com modelo real (`make eval`) pede `OPENAI_API_KEY` no ambiente. A integração com Postgres pede o banco de teste descrito no README do pacote.

## Limites que o código ainda carrega

O conjunto de avaliação da triagem continua o golden set sintético do curso. O aceite de recall em corpus humano rotulado não foi medido. O protocolo é uma linha por revisão: editar substitui a versão anterior, sem histórico e sem exportação PROSPERO. A busca executa a consulta que a pessoa escreve; não gera a string booleana por base. Se `model_auditor` não for informado, o Auditor usa o mesmo modelo do Triador.
