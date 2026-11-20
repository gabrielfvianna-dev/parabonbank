# Parabon Bank — Backend (API)

API em **Node.js + Express 5** usando o banco **MySQL `sistema_bancario`**.
Os nomes dos campos e as mensagens de erro são os mesmos do frontend (`app/cadastro.js` e `app/login.js`).

| Item | Versão |
|---|---|
| Node.js | 20.12 ou mais novo (testado no 24.18) |
| MySQL | 8.0.16 ou mais novo (testado no 8.0.46) |
| express | 5.3.0 |
| mysql2 | 3.24.6 |
| bcryptjs | 3.0.3 |
| helmet | 8.3.0 |
| cors | 2.8.6 |
| express-rate-limit | 8.7.1 |

## Como rodar

1. Rode o script SQL do banco no MySQL (Workbench), se ainda não rodou.
2. Na pasta `backend`:

```bash
npm install
```

3. Copie `.env.example` para `.env` e coloque a senha do seu MySQL em `DB_PASSWORD`.
4. Inicie a API:

```bash
npm start
```

5. Teste: abra http://localhost:3000/api/health. A resposta deve ser `{"status":"ok","database":"ok"}`.

## Segurança (criptografia)

| O quê | Como |
|---|---|
| Senha | **bcrypt** com custo 12 (`usuario_acesso.senha_hash`). A senha nunca é gravada. |
| Token de login | 256 bits aleatórios (`crypto.randomBytes`). O banco guarda só o **SHA-256** (`sessao.token_hash`). |
| PIN | Validado com as regras do front, mas **não é gravado**: o banco não tem coluna para ele. |
| Força bruta | 5 senhas erradas bloqueiam o acesso por 15 minutos (`tentativas_login` / `bloqueado_ate`), e há limite de requisições por IP. |
| Pix | Exige o token de login **e** a senha. As duas contas são travadas (`FOR UPDATE`) para não gastar o mesmo saldo duas vezes. |
| Dinheiro | Contas feitas em centavos inteiros (sem erro de arredondamento). |
| Auditoria | Cadastro, aceite dos termos, login, logout, chaves e Pix ficam na tabela `auditoria`. |
| HTTP | `helmet` (cabeçalhos de segurança), CORS restrito e corpo JSON de no máximo 10 KB. |

## Como o frontend usa a API

- Endereço: `http://localhost:3000` no navegador. No celular (Expo Go), use o IP do computador, por exemplo `http://192.168.0.10:3000`.
- Envie sempre `Content-Type: application/json`.
- Nas rotas protegidas, envie o header `Authorization: Bearer <token>` com o token recebido no login.
- **Erros** sempre vêm assim:

```json
{
  "message": "Verifique os dados informados.",
  "errors": { "cpf": "Informe um CPF válido." }
}
```

`errors` usa os mesmos nomes de campo do front. Por isso, na tela de cadastro, basta fazer `setErrors(resposta.errors)`.

## Rotas

| Método | Rota | Login? | Body (JSON) |
|---|---|---|---|
| GET | `/api/health` | não | — |
| POST | `/api/auth/cadastro` | não | [exemplos/cadastro.json](exemplos/cadastro.json) |
| POST | `/api/auth/login` | não | [exemplos/login.json](exemplos/login.json) |
| POST | `/api/auth/logout` | sim | — |
| GET | `/api/clientes/me` | sim | — |
| GET | `/api/contas` | sim | — |
| GET | `/api/contas/:id` | sim | — |
| GET | `/api/contas/:id/extrato?limit=50` | sim | — |
| GET | `/api/pix/chaves` | sim | — |
| POST | `/api/pix/chaves` | sim | [exemplos/pix-chave.json](exemplos/pix-chave.json) |
| DELETE | `/api/pix/chaves/:id` | sim | — |
| POST | `/api/pix/enviar` | sim | [exemplos/pix-enviar.json](exemplos/pix-enviar.json) |
| POST | `/api/dev/contas/:id/deposito` | sim | [exemplos/deposito-dev.json](exemplos/deposito-dev.json) (só com `HABILITAR_ROTAS_DEV=true`) |

### Cadastro: `POST /api/auth/cadastro`

O body tem exatamente os estados da tela de cadastro: `fullName`, `cpf`, `birthDate` (`DD-MM-AAAA`), `email`, `phone`, `password`, `confirmPassword`, `pin`, `confirmPin` e `termsAccepted`. O CPF e o telefone podem vir com máscara.

Quando dá certo, a API cria o `cliente`, o `usuario_acesso`, uma `conta` DIGITAL na agência 0001 e a `titularidade`. Resposta `201`:

```json
{
  "message": "Conta criada com sucesso.",
  "cliente": { "id": 3, "fullName": "Ana Paula Souza", "cpf": "52998224725", "birthDate": "15-03-1995",
               "email": "ana.souza@email.com", "phone": "12998887766", "status": "ATIVO" },
  "conta": { "id": 3, "bankCode": "999", "agency": "0001", "accountNumber": "48213377", "accountDigit": "5",
             "accountType": "DIGITAL", "balance": 0, "overdraftLimit": 0, "status": "ATIVA", "holderType": "TITULAR" }
}
```

Respostas de erro: `400` para campos inválidos e `409` para CPF ou e-mail já cadastrado.

### Login: `POST /api/auth/login`

O body é `{ "identifier": "e-mail ou CPF", "password": "..." }`. Resposta `200`:

```json
{ "message": "Login realizado com sucesso.", "token": "…", "tokenType": "Bearer",
  "expiresAt": "2026-10-20T02:43:00", "cliente": { … } }
```

Respostas de erro: `401` para e-mail/CPF ou senha inválidos e `423` para acesso bloqueado.

### Envio de Pix: `POST /api/pix/enviar`

```json
{ "key": "chave do destinatário", "amount": 50.25, "description": "opcional", "password": "senha", "accountId": 1 }
```

- `key` pode ser CPF, e-mail, telefone (com ou sem +55) ou chave aleatória.
- `amount` aceita `50.25`, `"50.25"` ou `"50,25"`. O máximo por Pix vem de `PIX_LIMITE_POR_TRANSACAO`.
- `accountId` é opcional. Se não vier, a API usa a conta principal.

Resposta `201`: `{ message, pix: { id, endToEndId, amount, status: "CONCLUIDO", recipient: {...} }, conta }`.

Respostas de erro: `400` para dados inválidos ou para a própria conta, `401` para senha errada, `404` para chave não encontrada e `422` para saldo insuficiente.

## Testes (Python)

Os testes chamam a API de verdade. Antes de rodar:

1. No `.env`, coloque `HABILITAR_ROTAS_DEV=true` (o depósito de teste é usado para ter saldo) e aumente os limites: `RATE_LIMIT_AUTH_MAX=5000` e `RATE_LIMIT_PIX_MAX=5000`.
2. Inicie a API com `npm start`.
3. Em outro terminal, dentro de `backend`:

```bash
python -m pip install -r testes/requirements.txt
```
```bash
python -m pytest testes -v
```

O que é testado:

- `test_cadastro.py`: validações iguais às do front, duplicidade e JSON inválido.
- `test_login.py`: login por e-mail e por CPF, mensagens, bloqueio após 5 tentativas e logout.
- `test_pix.py`: chaves, envio, extrato, saldo insuficiente, senha errada, acesso a contas de outras pessoas e Pix simultâneos.
- `test_criptografia.py`: lê o MySQL e confere que a senha está em bcrypt, que o token está só como SHA-256 e que o PIN não foi gravado.

> Os testes criam clientes de teste (e-mails `@parabon.test`) no banco configurado. Se quiser, use um banco separado para testes.

### Substituto da dashboard

```bash
python testes/enviar_exemplos.py
```

Esse script envia os JSON da pasta `exemplos/` na ordem do app (cadastro → login → chave Pix → depósito → Pix → extrato → logout) e mostra cada requisição e resposta no terminal.

## Estrutura

```
backend/
├── .env.example          configurações (copie para .env)
├── package.json
├── exemplos/             JSON de exemplo de cada requisição
├── src/
│   ├── server.js         inicia a API
│   ├── app.js            middlewares e rotas
│   ├── config.js         lê o .env
│   ├── db.js             conexão MySQL e transações
│   ├── validacoes.js     mesmas regras do front
│   ├── seguranca/criptografia.js
│   ├── middlewares/      autenticação e erros
│   ├── servicos/         contas, auditoria e tentativas de login
│   ├── rotas/            auth, clientes, contas, pix e dev
│   └── utils/            dinheiro, formatadores e erros
└── testes/               pytest + enviar_exemplos.py
```

## Limitações por causa do banco (que não foi alterado)

- **PIN:** não existe coluna para ele, então não é gravado. Por isso o Pix é confirmado com a **senha**. Se um dia for criada uma coluna `pin_hash`, dá para trocar.
- **Usuários de exemplo do script (Maria e João):** o `senha_hash` deles é um texto falso, então não conseguem fazer login. Use contas criadas pelo cadastro.
- **Endereço, renda, profissão:** o front ainda não coleta esses dados, então as colunas ficam com o valor padrão.
