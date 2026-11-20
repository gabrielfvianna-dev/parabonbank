"""Funções de apoio usadas pelos testes e pelo script enviar_exemplos.py."""

import json
import os
import random
import uuid
from pathlib import Path

import requests

PASTA_BACKEND = Path(__file__).resolve().parent.parent
PASTA_EXEMPLOS = PASTA_BACKEND / "exemplos"

SENHA_PADRAO = "Senha@123"


def ler_env():
    """Lê o backend/.env (se existir). Variáveis do sistema têm prioridade."""
    valores = {}
    arquivo = PASTA_BACKEND / ".env"

    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                valores[chave.strip()] = valor.strip()

    for chave in ("PORT", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        if chave in os.environ:
            valores[chave] = os.environ[chave]

    return valores


ENV = ler_env()
BASE_URL = os.environ.get("API_URL") or f"http://localhost:{ENV.get('PORT', '3000')}"


def exemplo(nome):
    """Carrega um JSON da pasta backend/exemplos."""
    return json.loads((PASTA_EXEMPLOS / nome).read_text(encoding="utf-8"))


def gerar_cpf(com_mascara=False):
    """Gera um CPF aleatório VÁLIDO (com os dígitos verificadores corretos)."""
    while True:
        numeros = [random.randint(0, 9) for _ in range(9)]
        if len(set(numeros)) > 1:
            break

    for tamanho in (9, 10):
        soma = sum(n * (tamanho + 1 - i) for i, n in enumerate(numeros[:tamanho]))
        resto = (soma * 10) % 11
        numeros.append(0 if resto == 10 else resto)

    cpf = "".join(map(str, numeros))
    if com_mascara:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf


def gerar_telefone():
    return "129" + "".join(str(random.randint(0, 9)) for _ in range(8))


def dados_cadastro(**alteracoes):
    """Monta o JSON da tela de cadastro com CPF/e-mail/telefone únicos."""
    dados = exemplo("cadastro.json")
    sufixo = uuid.uuid4().hex[:10]
    dados.update(
        {
            "cpf": gerar_cpf(),
            "email": f"teste.{sufixo}@parabon.test",
            "phone": gerar_telefone(),
            "password": SENHA_PADRAO,
            "confirmPassword": SENHA_PADRAO,
        }
    )
    dados.update(alteracoes)
    return dados


class Api:
    """Cliente HTTP simples para a API."""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.sessao = requests.Session()

    def chamar(self, metodo, caminho, json=None, token=None, **kwargs):
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.sessao.request(
            metodo, f"{self.base_url}{caminho}", json=json, headers=headers, timeout=30, **kwargs
        )

    def get(self, caminho, **kwargs):
        return self.chamar("GET", caminho, **kwargs)

    def post(self, caminho, json=None, **kwargs):
        return self.chamar("POST", caminho, json=json, **kwargs)

    def delete(self, caminho, **kwargs):
        return self.chamar("DELETE", caminho, **kwargs)

    def criar_usuario(self, **alteracoes):
        """Cadastra e faz login. Retorna dict com dados, token, cliente e conta."""
        dados = dados_cadastro(**alteracoes)
        resposta = self.post("/api/auth/cadastro", dados)
        assert resposta.status_code == 201, resposta.text

        login = self.post(
            "/api/auth/login",
            {"identifier": dados["email"], "password": dados["password"]},
        )
        assert login.status_code == 200, login.text

        return {
            "dados": dados,
            "token": login.json()["token"],
            "cliente": resposta.json()["cliente"],
            "conta": resposta.json()["conta"],
        }

    def depositar(self, usuario, valor):
        resposta = self.post(
            f"/api/dev/contas/{usuario['conta']['id']}/deposito",
            {"amount": valor},
            token=usuario["token"],
        )
        assert resposta.status_code == 201, (
            f"{resposta.status_code} {resposta.text} — "
            "o depósito de teste exige HABILITAR_ROTAS_DEV=true no .env"
        )
        return resposta.json()["conta"]

    def saldo(self, usuario):
        resposta = self.get(f"/api/contas/{usuario['conta']['id']}", token=usuario["token"])
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["conta"]["balance"]
