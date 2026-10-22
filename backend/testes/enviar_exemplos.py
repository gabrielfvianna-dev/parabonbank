"""Substitui a dashboard enquanto ela não existe.

Envia os JSON da pasta backend/exemplos para a API, na ordem que o app faria,
e mostra cada requisição e resposta no terminal:

  1. cadastro de duas pessoas (remetente e destinatário)
  2. login
  3. dados do cliente (/clientes/me)
  4. cadastro de chave Pix do destinatário
  5. depósito de teste (só se HABILITAR_ROTAS_DEV=true)
  6. envio de Pix
  7. extrato das duas contas
  8. logout

Uso (com a API rodando):
    python testes/enviar_exemplos.py
"""

import json
import sys

from apoio import BASE_URL, Api, dados_cadastro, exemplo

# Cores no terminal (funcionam no Windows Terminal / PowerShell moderno).
VERDE, VERMELHO, AZUL, CINZA, FIM = "\033[92m", "\033[91m", "\033[94m", "\033[90m", "\033[0m"


def mostrar(titulo, metodo, caminho, corpo, resposta):
    cor = VERDE if resposta.status_code < 400 else VERMELHO
    print(f"\n{AZUL}━━ {titulo} ━━{FIM}")
    print(f"{metodo} {caminho}")

    if corpo is not None:
        visivel = {k: ("******" if k in {"password", "confirmPassword", "pin", "confirmPin"} else v)
                   for k, v in corpo.items()}
        print(f"{CINZA}{json.dumps(visivel, ensure_ascii=False, indent=2)}{FIM}")

    print(f"{cor}← {resposta.status_code}{FIM}")
    try:
        print(json.dumps(resposta.json(), ensure_ascii=False, indent=2))
    except ValueError:
        print(resposta.text)


def chamar(api, titulo, metodo, caminho, corpo=None, token=None):
    resposta = api.chamar(metodo, caminho, json=corpo, token=token)
    mostrar(titulo, metodo, caminho, corpo, resposta)
    return resposta


def main():
    api = Api()
    print(f"API: {BASE_URL}")

    try:
        saude = api.get("/api/health")
    except Exception:
        print(f"{VERMELHO}A API não está respondendo. Rode 'npm start' na pasta backend.{FIM}")
        sys.exit(1)

    mostrar("Saúde da API", "GET", "/api/health", None, saude)

    # O exemplo de cadastro é usado como base, trocando CPF/e-mail/telefone
    # para não dar "já cadastrado" quando o script roda mais de uma vez.
    remetente = dados_cadastro(fullName="Ana Paula Souza")
    destinatario = dados_cadastro(fullName="Bruno Lima")

    chamar(api, "1. Cadastro do remetente", "POST", "/api/auth/cadastro", remetente)
    cadastro_dest = chamar(api, "1. Cadastro do destinatário", "POST", "/api/auth/cadastro", destinatario)

    login = exemplo("login.json")
    login["identifier"] = remetente["email"]
    resposta_login = chamar(api, "2. Login do remetente", "POST", "/api/auth/login", login)

    if resposta_login.status_code != 200:
        sys.exit(1)

    token = resposta_login.json()["token"]
    token_dest = api.post(
        "/api/auth/login",
        {"identifier": destinatario["email"], "password": destinatario["password"]},
    ).json()["token"]

    me = chamar(api, "3. Dados do cliente logado", "GET", "/api/clientes/me", token=token)
    conta_id = me.json()["contas"][0]["id"]
    conta_dest_id = cadastro_dest.json()["conta"]["id"]

    chamar(api, "4. Chave Pix do destinatário", "POST", "/api/pix/chaves",
           exemplo("pix-chave.json"), token=token_dest)

    deposito = chamar(api, "5. Depósito de teste", "POST", f"/api/dev/contas/{conta_id}/deposito",
                      exemplo("deposito-dev.json"), token=token)

    if deposito.status_code == 404:
        print(f"{VERMELHO}Depósito indisponível: coloque HABILITAR_ROTAS_DEV=true no .env "
              f"para testar um Pix com saldo.{FIM}")

    pix = exemplo("pix-enviar.json")
    pix["key"] = destinatario["email"]
    pix["password"] = remetente["password"]
    chamar(api, "6. Envio de Pix", "POST", "/api/pix/enviar", pix, token=token)

    chamar(api, "7. Extrato do remetente", "GET", f"/api/contas/{conta_id}/extrato", token=token)
    chamar(api, "7. Extrato do destinatário", "GET", f"/api/contas/{conta_dest_id}/extrato", token=token_dest)

    chamar(api, "8. Logout", "POST", "/api/auth/logout", token=token)


if __name__ == "__main__":
    main()
