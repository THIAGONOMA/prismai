# prismai-web

Interface do copiloto de revisão sistemática. O backend está em `../prismai`. A licença é a MIT desse pacote: [../prismai/LICENSE](../prismai/LICENSE).

## O que a tela faz

O login troca usuário e senha por um token da API. A primeira conta é criada em `POST /v1/auth/register`, como descrito no README do `prismai`.

A home lista as revisões e cria uma nova pelo identificador. Dentro de uma revisão, as abas são:

- Protocolo
- Triagem
- Full-text
- Extração
- Síntese
- GRADE
- Relatório
- Living

## Desenvolvimento

```bash
npm install
npm run dev
```

A interface fala com `http://localhost:8000` salvo se `NEXT_PUBLIC_API_URL` estiver definida antes do build. No `docker compose` do `prismai`, esse valor entra como argumento de build.
