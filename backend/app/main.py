"""Monta a API: proteções, tratamento de erros e rotas.

Ordem do que acontece em cada requisição:

    1. CORS                → só origens liberadas no .env podem chamar pelo navegador
    2. Limite por IP       → login, cadastro e Pix (força bruta)
    3. Corpo JSON          → no máximo 10 KB, precisa ser JSON válido
    4. Autenticação        → rotas protegidas conferem o token na tabela sessao
    5. Rota                → valida, criptografa, consulta o MySQL
    6. Cabeçalhos          → toda resposta sai com cabeçalhos de segurança e sem cache
    7. Erros               → sempre no formato { message, errors }, sem detalhes internos
"""

import logging

import pymysql
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.banco import abrir_conexao
from app.erros import MSG_DADOS_INVALIDOS, ErroApi
from app.rotas import auth, clientes, contas, dev, pix
from app.seguranca.http import cabecalhos_de_seguranca

# Se faltar a pimenta das senhas (ou o certificado do HTTPS), a API nem liga.
config.conferir_configuracao()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("parabon")

app = FastAPI(
    title="API Parabon Bank",
    version="2.0.0",
    # A documentação automática (/docs) mostra todas as rotas.
    # Útil para estudar, mas não deve ficar pública: só aparece em desenvolvimento.
    docs_url="/docs" if config.HABILITAR_ROTAS_DEV else None,
    redoc_url=None,
    openapi_url="/openapi.json" if config.HABILITAR_ROTAS_DEV else None,
)

# Permite que o Expo web (navegador) chame a API.
# O app no celular (Expo Go) não depende de CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
app.middleware("http")(cabecalhos_de_seguranca)


# ------------------------------------------------------------
# Tratamento de erros: o app SEMPRE recebe { message, errors? }.
# ------------------------------------------------------------
@app.exception_handler(ErroApi)
async def erro_da_api(request: Request, erro: ErroApi):
    return JSONResponse(erro.corpo(), status_code=erro.status, headers=erro.headers)


@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, erro: StarletteHTTPException):
    if erro.status_code == 404:
        return JSONResponse({"message": "Rota não encontrada."}, status_code=404)

    if erro.status_code == 405:
        return JSONResponse({"message": "Método não permitido nesta rota."}, status_code=405)

    return JSONResponse({"message": str(erro.detail)}, status_code=erro.status_code)


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, erro: RequestValidationError):
    return JSONResponse({"message": MSG_DADOS_INVALIDOS}, status_code=400)


@app.exception_handler(pymysql.err.OperationalError)
async def banco_fora_do_ar(request: Request, erro: pymysql.err.OperationalError):
    # MySQL desligado, senha errada no .env, conexão caiu... O problema é do servidor,
    # não do usuário: responde 503 ("tente de novo daqui a pouco").
    log.error("banco indisponível em %s %s: %s", request.method, request.url.path, erro)
    return JSONResponse(
        {"message": "Serviço temporariamente indisponível. Tente novamente em instantes."},
        status_code=503,
    )


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, erro: Exception):
    # O detalhe vai só para o terminal do servidor. O usuário recebe uma mensagem genérica,
    # sem nome de tabela, SQL ou caminho de arquivo, que ajudariam um atacante.
    log.exception("erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse({"message": "Erro interno. Tente novamente mais tarde."}, status_code=500)


# ------------------------------------------------------------
# GET /api/health: a API e o banco estão funcionando?
# ------------------------------------------------------------
@app.get("/api/health")
def saude():
    try:
        con = abrir_conexao()
        try:
            with con.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            con.close()
    except Exception as erro:
        log.error("banco indisponível: %s", erro)
        return JSONResponse({"status": "erro", "database": "indisponível"}, status_code=503)

    return {"status": "ok", "database": "ok"}


# ------------------------------------------------------------
# Rotas
# ------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth")
app.include_router(clientes.router, prefix="/api/clientes")
app.include_router(contas.router, prefix="/api/contas")
app.include_router(pix.router, prefix="/api/pix")

if config.HABILITAR_ROTAS_DEV:
    app.include_router(dev.router, prefix="/api/dev")
    log.warning("ATENÇÃO: rotas de desenvolvimento (/api/dev) e /docs habilitadas.")
