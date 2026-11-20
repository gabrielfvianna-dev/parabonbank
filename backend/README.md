# Parabon Bank — Backend (API em Python)

API em **Python + FastAPI** usando o banco **MySQL `sistema_bancario`**.
Os nomes dos campos e as mensagens de erro são os mesmos do frontend (`app/cadastro.js` e `app/login.js`).

📖 Documentação completa (segurança, rotas, `.env`, HTTPS): [docs/backend.md](../docs/backend.md)
🛠️ Passo a passo para rodar: [docs/como-rodar.md](../docs/como-rodar.md)

## Começo rápido

Dentro da pasta `backend`:

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Preencha no `.env` a `DB_PASSWORD` (senha do seu MySQL) e a `SENHA_PEPPER`. Para gerar a pepper:

```bash
.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ligue a API:

```bash
.venv/Scripts/python iniciar.py --dev
```

Teste em http://localhost:3000/api/health. A resposta deve ser `{"status":"ok","database":"ok"}`.

## Testes

```bash
.venv/Scripts/python -m pytest testes/test_unidade_seguranca.py -v
```

Esses não precisam da API nem do banco. Para a bateria completa (API ligada, `HABILITAR_ROTAS_DEV=true` e limites altos no `.env`):

```bash
.venv/Scripts/python -m pytest testes -v
```

## Backend antigo

O backend anterior, em Node.js, está guardado em `_legado_node/` só para consulta. Ele não é usado. Quando o grupo não precisar mais dele, a pasta pode ser apagada.
