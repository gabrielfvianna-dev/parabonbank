"""Proteções na entrada e na saída de cada requisição HTTP.

Entrada: o corpo precisa ser JSON e ter no máximo 10 KB.
Saída: toda resposta leva cabeçalhos de segurança e a ordem de NÃO guardar cache
(dados bancários e tokens não podem ficar salvos em cache de navegador ou proxy).
"""

import json

from fastapi import Request

from app import config
from app.erros import ErroApi

LIMITE_CORPO = 10 * 1024  # 10 KB é muito mais do que qualquer tela do app envia


def _recusar_constante(valor):
    # O JSON padrão não tem NaN nem Infinity; o Python aceitaria, então barramos aqui.
    raise ValueError(f"valor não permitido: {valor}")


async def corpo_json(request: Request) -> dict:
    """Lê o corpo da requisição como JSON, com limite de tamanho.

    Devolve sempre um dicionário. Se o app mandar outra coisa (lista, número...),
    devolve {} e as validações da rota respondem com os campos que faltam.
    """
    tamanho = request.headers.get("content-length", "")

    if tamanho.isdigit() and int(tamanho) > LIMITE_CORPO:
        raise ErroApi(413, "Requisição muito grande.")

    # Lê aos poucos: se passar do limite, para na hora (não enche a memória).
    dados = bytearray()

    async for pedaco in request.stream():
        dados += pedaco
        if len(dados) > LIMITE_CORPO:
            raise ErroApi(413, "Requisição muito grande.")

    if not dados.strip():
        return {}

    tipo = request.headers.get("content-type", "").split(";")[0].strip().lower()

    if tipo != "application/json":
        raise ErroApi(415, "Envie os dados em JSON (Content-Type: application/json).")

    try:
        valor = json.loads(dados.decode("utf-8"), parse_constant=_recusar_constante)
    except (UnicodeDecodeError, ValueError):
        raise ErroApi(400, "JSON inválido.") from None

    return valor if isinstance(valor, dict) else {}


def ip_do_cliente(request: Request):
    """IP de quem fez a requisição (gravado na auditoria, máximo 45 caracteres)."""
    return request.client.host[:45] if request.client else None


async def cabecalhos_de_seguranca(request: Request, call_next):
    """Middleware: acrescenta cabeçalhos de segurança em todas as respostas."""
    resposta = await call_next(request)
    h = resposta.headers

    # Não deixa o navegador "adivinhar" o tipo do conteúdo.
    h["X-Content-Type-Options"] = "nosniff"
    # A API não pode ser aberta dentro de outra página (clickjacking).
    h["X-Frame-Options"] = "DENY"
    # Não vaza o endereço da API para outros sites.
    h["Referrer-Policy"] = "no-referrer"
    # Isola a API de outras janelas e origens.
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    h["Cross-Origin-Resource-Policy"] = "same-origin"
    # Respostas com dados bancários/tokens nunca ficam guardadas em cache.
    h["Cache-Control"] = "no-store"
    h["Pragma"] = "no-cache"

    # A API só devolve JSON: não precisa carregar nenhum script, imagem ou estilo.
    # (A documentação /docs, que só existe em desenvolvimento, precisa de scripts.)
    if not request.url.path.startswith(("/docs", "/openapi.json")):
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    # Com HTTPS ligado, avisa o navegador para nunca mais usar http:// com esta API.
    if config.HTTPS_ATIVO:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return resposta
