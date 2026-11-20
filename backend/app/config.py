"""Configurações da API, lidas do arquivo backend/.env.

Tudo que muda de um computador para outro (senha do MySQL, porta, chaves secretas)
fica no .env, e nunca no código. Assim nenhum segredo vai parar no Git.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Pasta backend/ (este arquivo está em backend/app/config.py).
PASTA_BACKEND = Path(__file__).resolve().parent.parent

# Carrega o .env, se ele existir. Variáveis já definidas no sistema têm prioridade.
load_dotenv(PASTA_BACKEND / ".env")


# Lê um número do .env; se estiver vazio ou inválido, usa o valor padrão.
def _numero(nome, padrao):
    valor = os.getenv(nome, "").strip()

    try:
        return int(valor) if valor else padrao
    except ValueError:
        return padrao


# Lê um "true"/"false" do .env.
def _booleano(nome, padrao=False):
    valor = os.getenv(nome, "").strip().lower()
    return valor == "true" if valor else padrao


# Lê um texto do .env, tirando espaços das pontas.
def _texto(nome, padrao=""):
    return os.getenv(nome, padrao).strip()


# Porta da API (o frontend chama http://IP:3000).
PORTA = _numero("PORT", 3000)

# Conexão com o MySQL.
DB_HOST = _texto("DB_HOST", "localhost")
DB_PORT = _numero("DB_PORT", 3306)
DB_USER = _texto("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")  # sem strip: senha pode ter espaço
DB_NAME = _texto("DB_NAME", "sistema_bancario")

# Agência onde as contas novas são abertas (precisa existir no banco: seção 13 do SQL).
BANCO_CODIGO = _texto("BANCO_CODIGO", "999")
AGENCIA_CODIGO = _texto("AGENCIA_CODIGO", "0001")

# "Pimenta" (pepper) das senhas: uma chave secreta que fica SÓ no servidor.
# Mesmo que alguém copie o banco inteiro, sem esta chave não dá nem para
# tentar adivinhar as senhas. Se ela for perdida ou trocada, ninguém consegue
# mais fazer login, então guarde uma cópia em lugar seguro.
SENHA_PEPPER = os.getenv("SENHA_PEPPER", "")

# Sessão e bloqueio de login.
SESSAO_MINUTOS = _numero("SESSAO_MINUTOS", 480)
LOGIN_MAX_TENTATIVAS = _numero("LOGIN_MAX_TENTATIVAS", 5)
LOGIN_BLOQUEIO_MINUTOS = _numero("LOGIN_BLOQUEIO_MINUTOS", 15)

# Limite de requisições por IP.
RATE_LIMIT_AUTH_MAX = _numero("RATE_LIMIT_AUTH_MAX", 20)  # login + cadastro a cada 15 min
RATE_LIMIT_PIX_MAX = _numero("RATE_LIMIT_PIX_MAX", 30)  # envios de Pix por minuto

# Valor máximo de um único Pix (R$).
PIX_LIMITE_POR_TRANSACAO = _numero("PIX_LIMITE_POR_TRANSACAO", 10000)

# Origens liberadas para chamar a API pelo navegador (Expo web).
CORS_ORIGINS = [
    origem.strip()
    for origem in _texto(
        "CORS_ORIGINS", "http://localhost:8081,http://localhost:19006"
    ).split(",")
    if origem.strip()
]

# HTTPS: caminhos do certificado e da chave. Se os dois estiverem preenchidos,
# a API passa a responder só em https:// (tudo criptografado no caminho).
HTTPS_CERT = _texto("HTTPS_CERT")
HTTPS_KEY = _texto("HTTPS_KEY")
HTTPS_ATIVO = bool(HTTPS_CERT and HTTPS_KEY)

# Rotas de desenvolvimento (depósito de teste) e documentação automática (/docs).
# NUNCA deixe "true" em produção.
HABILITAR_ROTAS_DEV = _booleano("HABILITAR_ROTAS_DEV")


def conferir_configuracao():
    """Impede a API de subir com uma configuração insegura.

    É melhor a API nem ligar do que ligar sem proteção.
    """
    problemas = []

    if len(SENHA_PEPPER) < 32:
        problemas.append(
            "SENHA_PEPPER precisa ter pelo menos 32 caracteres. Gere uma com:\n"
            '    python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )

    if HTTPS_ATIVO:
        for nome, caminho in (("HTTPS_CERT", HTTPS_CERT), ("HTTPS_KEY", HTTPS_KEY)):
            if not (PASTA_BACKEND / caminho).exists() and not Path(caminho).exists():
                problemas.append(f"{nome} aponta para um arquivo que não existe: {caminho}")

    if problemas:
        raise SystemExit(
            "Configuração inválida no backend/.env:\n- " + "\n- ".join(problemas)
        )


def caminho_arquivo(caminho):
    """Aceita caminho relativo à pasta backend/ ou caminho absoluto."""
    relativo = PASTA_BACKEND / caminho
    return str(relativo if relativo.exists() else Path(caminho))
