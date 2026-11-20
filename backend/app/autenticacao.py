"""Proteção das rotas que exigem login.

O app envia em toda requisição protegida o cabeçalho:

    Authorization: Bearer <token>

A API calcula o SHA-256 do token e procura esse hash na tabela sessao.
Só passa se a sessão estiver ATIVA, dentro da validade, e se o cliente
e o usuário ainda estiverem ATIVOS.
"""

from dataclasses import dataclass

from fastapi import Depends, Request

from app.banco import buscar_um, conexao, executar
from app.erros import ErroApi
from app.seguranca.tokens import hash_token, token_parece_valido

# Avisa o cliente HTTP que esta rota espera um token Bearer (padrão RFC 6750).
_PEDIR_TOKEN = {"WWW-Authenticate": "Bearer"}


@dataclass
class UsuarioLogado:
    sessao_id: int
    cliente_id: int
    usuario_id: int


def usuario_logado(request: Request, con=Depends(conexao)) -> UsuarioLogado:
    """Dependência do FastAPI: descobre quem está logado ou responde 401."""
    tipo, _, token = request.headers.get("authorization", "").partition(" ")
    token = token.strip()

    if tipo.lower() != "bearer" or not token:
        raise ErroApi(401, "Faça login para continuar.", headers=_PEDIR_TOKEN)

    # Token com formato impossível nem chega a ir para o banco.
    if not token_parece_valido(token):
        raise ErroApi(401, "Sessão inválida. Faça login novamente.", headers=_PEDIR_TOKEN)

    sessao = buscar_um(
        con,
        """SELECT s.id AS sessao_id, s.cliente_id, s.expiracao <= NOW() AS expirada,
                  cl.status AS cliente_status, ua.id AS usuario_id,
                  ua.status AS usuario_status
             FROM sessao s
             JOIN cliente cl ON cl.id = s.cliente_id
             JOIN usuario_acesso ua ON ua.cliente_id = cl.id
            WHERE s.token_hash = %s AND s.status = 'ATIVA'""",
        (hash_token(token),),
    )

    if not sessao:
        raise ErroApi(401, "Sessão inválida. Faça login novamente.", headers=_PEDIR_TOKEN)

    if int(sessao["expirada"]) == 1:
        # Marca a sessão como expirada para ela nunca mais ser aceita.
        executar(con, "UPDATE sessao SET status = 'EXPIRADA' WHERE id = %s", (sessao["sessao_id"],))
        raise ErroApi(401, "Sessão expirada. Faça login novamente.", headers=_PEDIR_TOKEN)

    if sessao["cliente_status"] != "ATIVO" or sessao["usuario_status"] != "ATIVO":
        raise ErroApi(403, "Acesso não permitido. Entre em contato com o banco.")

    return UsuarioLogado(
        sessao_id=int(sessao["sessao_id"]),
        cliente_id=int(sessao["cliente_id"]),
        usuario_id=int(sessao["usuario_id"]),
    )
