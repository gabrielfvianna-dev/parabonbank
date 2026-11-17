# Tutorial: como rodar o Parabon Bank

Ordem: **1. instalar programas → 2. banco → 3. backend → 4. frontend → 5. testes (opcional)**.

Você vai precisar de **dois terminais abertos ao mesmo tempo**: um para o backend e outro para o frontend.

---

## 1. Programas necessários

| Programa | Versão | Para quê | Conferir |
|---|---|---|---|
| [Node.js](https://nodejs.org) (LTS) | 20.12 ou mais novo | Backend e frontend | `node -v` |
| [MySQL Server + Workbench](https://dev.mysql.com/downloads/installer/) | 8.0.16 ou mais novo | Banco de dados | Abra o Workbench e conecte |
| [Expo Go](https://expo.dev/go) no celular | Compatível com SDK 54 | Abrir o app | Loja do celular |
| [Python 3](https://www.python.org/downloads/) | 3.10+ | Só para os testes | `python --version` |
| VS Code (sugestão) | — | Editar o código | — |

```bash
node -v
```

```bash
npm -v
```

---

## 2. Banco de dados (MySQL)

1. Abra o **MySQL Workbench** e entre na sua conexão local (normalmente `root@localhost:3306`).
2. Menu **File → Open SQL Script...** e abra `database/bancodedados.sql`.
3. ⚠️ **Não execute o arquivo inteiro.** O final do script (seção 14) **apaga todos os dados**. Faça assim:
   - Clique no começo da linha 1.
   - Role até o fim da **seção 13 (DADOS INICIAIS)**, logo antes do bloco `-- 14. LIMPEZA DOS DADOS DE TESTE` (por volta da linha 662), e clique ali segurando **Shift** para selecionar tudo.
   - Execute só a seleção: **Ctrl + Shift + Enter** (ou o raio ⚡ com a seleção ativa).
4. Confira se deu certo rodando:

```sql
USE sistema_bancario;
SELECT codigo_banco, nome FROM banco;      -- deve mostrar 999 | Parabon Bank
SELECT codigo_agencia, nome FROM agencia;  -- deve mostrar 0001 | Agência Central
```

> **Precisa recriar do zero?** Execute `DROP DATABASE sistema_bancario;` (apaga tudo) e repita o passo 3.
>
> **Rodou o arquivo inteiro sem querer?** As tabelas ficaram vazias. Faça o `DROP DATABASE` acima e rode de novo só até a seção 13.

---

## 3. Backend (API)

Terminal 1, a partir da pasta do projeto:

```bash
cd backend
```

```bash
npm install
```

Crie o arquivo de configuração copiando o modelo (se o `.env` ainda não existir):

```bash
cp .env.example .env
```

Abra `backend/.env` e preencha **pelo menos**:

```ini
DB_USER=root
DB_PASSWORD=a_senha_do_seu_mysql
```

Suba a API:

```bash
npm run dev
```

O terminal deve mostrar `API do Parabon Bank rodando em http://localhost:3000`.

**Teste:** abra http://localhost:3000/api/health no navegador. O esperado é:

```json
{"status":"ok","database":"ok"}
```

| Se aparecer... | Faça |
|---|---|
| `"database":"indisponível"` | Confira `DB_USER`, `DB_PASSWORD` e se o MySQL está ligado |
| `process.loadEnvFile is not a function` | Atualize o Node.js para 20.12+ |
| `EADDRINUSE :3000` | Já tem algo na porta 3000. Feche o outro terminal ou mude `PORT` no `.env` |

**Deixe esse terminal aberto.**

---

## 4. Frontend (Expo)

### 4.1 Descobrir o IP do computador

O app roda no celular, então ele precisa do IP do seu PC na rede Wi-Fi (não serve `localhost`).

```bash
ipconfig
```

Procure o adaptador **Wi-Fi** → **Endereço IPv4** (algo como `192.168.0.15`).

### 4.2 Configurar o endereço da API

Abra [`frontend/services/api.js`](../frontend/services/api.js) e troque o IP:

```js
const API_URL = "http://192.168.0.15:3000"; // ← seu IP + porta do backend
```

> Seu IP pode mudar quando você troca de rede (casa, faculdade, hotspot). Se o app parar de conectar, confira de novo com `ipconfig`.

### 4.3 Rodar

Terminal 2, a partir da pasta do projeto:

```bash
cd frontend
```

```bash
npm install
```

```bash
npx expo start
```

Abra o **Expo Go** no celular e leia o QR Code que aparece no terminal.

**Checklist se o app não conectar na API:**

- [ ] Celular e computador estão **na mesma rede Wi-Fi**.
- [ ] O backend está rodando (Terminal 1) e `/api/health` responde no PC.
- [ ] No navegador do **celular**, `http://SEU_IP:3000/api/health` abre. Se não abrir, é rede ou firewall.
- [ ] O **Firewall do Windows** liberou o Node.js em **redes privadas** (aparece um aviso na primeira vez que a API sobe; se você negou, libere em *Firewall do Windows → Permitir um aplicativo*).
- [ ] A rede do Windows está como **Privada**, não Pública.
- [ ] Se a rede bloquear tudo (Wi-Fi de faculdade, por exemplo), rode `npx expo start --tunnel`. Mas a API continua precisando ser acessível pelo IP: o mais fácil é usar o hotspot do celular.

> **Emulador Android** (Android Studio): use `const API_URL = "http://10.0.2.2:3000";` e rode `npm run android`.

### 4.4 Testando o fluxo

1. **Criar conta** → preencha tudo (senha com maiúscula, minúscula, número e símbolo; PIN de 6 dígitos sem sequência).
2. **Entrar** com o e-mail ou o CPF e a senha.
3. O **dashboard** mostra o saldo (R$ 0,00 em uma conta nova) e as movimentações.

Para ter saldo e testar Pix, veja o depósito de teste na seção 5.

---

## 5. Testes automáticos (opcional)

1. No `backend/.env`, ajuste:

```ini
HABILITAR_ROTAS_DEV=true
RATE_LIMIT_AUTH_MAX=5000
RATE_LIMIT_PIX_MAX=5000
```

2. Reinicie o backend (Ctrl + C no Terminal 1 e `npm run dev` de novo).
3. Em um terceiro terminal, dentro de `backend/`:

```bash
python -m pip install -r testes/requirements.txt
```

```bash
python -m pytest testes -v
```

Para ver o fluxo completo do app no terminal (cadastro → login → chave Pix → depósito → Pix → extrato → logout):

```bash
python testes/enviar_exemplos.py
```

> Os testes criam clientes com e-mail `@parabon.test` no banco. **Quando terminar, volte `HABILITAR_ROTAS_DEV=false`** e os limites para 20 e 30.

---

## 6. Deixando tudo arrumado

**Todo dia, para trabalhar:**

1. MySQL ligado (ele costuma iniciar sozinho com o Windows).
2. Terminal 1: `cd backend` → `npm run dev`
3. Terminal 2: `cd frontend` → `npx expo start`
4. Conferir o IP em `services/api.js` se mudou de rede.

**Boas práticas do projeto:**

| Faça | Não faça |
|---|---|
| Commitar o `.env.example` quando criar uma variável nova | Commitar o `.env` (tem senha) |
| Usar `theme.colors.*` e `theme.spacing.*` nas telas | Escrever cores e tamanhos direto no estilo |
| Manter os nomes de campo iguais no front e no back (`fullName`, `cpf`...) | Renomear um campo só de um lado |
| Rodar `npm run lint` no frontend antes de entregar | Rodar `npm run reset-project` (o script não existe mais; ele serviria para mover as telas para outra pasta) |
| Fazer backup antes de rodar a seção 14 do SQL | Rodar o SQL inteiro de uma vez |
| Deixar `HABILITAR_ROTAS_DEV=false` fora dos testes | Subir para produção com as rotas dev ligadas |

**Onde está cada coisa:**

| Pasta | Conteúdo | Documentação |
|---|---|---|
| `database/` | Script do MySQL | [banco-de-dados.md](banco-de-dados.md) |
| `backend/` | API Node.js | [backend.md](backend.md) |
| `frontend/` | App Expo | [frontend.md](frontend.md) |
| `docs/` | Esta documentação | [README.md](README.md) |
