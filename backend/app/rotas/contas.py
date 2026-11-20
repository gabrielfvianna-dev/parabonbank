"""Contas e extrato do cliente logado.

Toda rota confere se a conta pedida é mesmo do cliente logado.
Trocar o número na URL (/api/contas/2, /api/contas/3...) não mostra conta de ninguém.
"""

from fastapi import APIRouter, Depends

from app.autenticacao import UsuarioLogado, usuario_logado
from app.banco import buscar_todos, conexao
from app.servicos.contas import buscar_conta_do_cliente, listar_contas
from app.utils.formatadores import formatar_conta, formatar_transacao

router = APIRouter()


# GET /api/contas — todas as contas do cliente logado.
@router.get("")
def minhas_contas(logado: UsuarioLogado = Depends(usuario_logado), con=Depends(conexao)):
    contas = listar_contas(con, logado.cliente_id)
    return {"contas": [formatar_conta(conta) for conta in contas]}


# GET /api/contas/{id} — uma conta, com o saldo atualizado.
@router.get("/{conta_id}")
def uma_conta(conta_id: str, logado: UsuarioLogado = Depends(usuario_logado), con=Depends(conexao)):
    conta = buscar_conta_do_cliente(con, conta_id, logado.cliente_id)
    return {"conta": formatar_conta(conta)}


# GET /api/contas/{id}/extrato?limit=50 — últimas movimentações (mais novas primeiro).
@router.get("/{conta_id}/extrato")
def extrato(
    conta_id: str,
    limit: str = "50",
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    conta = buscar_conta_do_cliente(con, conta_id, logado.cliente_id)

    # Aceita de 1 a 200; qualquer valor estranho vira 50.
    limite = int(limit) if limit.isdigit() else 50
    limite = min(max(limite, 1), 200)

    transacoes = buscar_todos(
        con,
        """SELECT * FROM transacao
            WHERE conta_id = %s
            ORDER BY data_hora DESC, id DESC
            LIMIT %s""",
        (conta["id"], limite),
    )

    return {
        "conta": formatar_conta(conta),
        "transacoes": [formatar_transacao(t) for t in transacoes],
    }
