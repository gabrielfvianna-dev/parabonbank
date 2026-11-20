"""Dados do cliente logado (usado pelo dashboard)."""

from fastapi import APIRouter, Depends

from app.autenticacao import UsuarioLogado, usuario_logado
from app.banco import buscar_um, conexao
from app.servicos.contas import listar_contas
from app.utils.formatadores import formatar_cliente, formatar_conta

router = APIRouter()


# ------------------------------------------------------------
# GET /api/clientes/me — cliente logado + as contas dele.
# O dashboard usa cliente.fullName e contas[0] (a conta principal).
# ------------------------------------------------------------
@router.get("/me")
def meus_dados(logado: UsuarioLogado = Depends(usuario_logado), con=Depends(conexao)):
    cliente = buscar_um(con, "SELECT * FROM cliente WHERE id = %s", (logado.cliente_id,))
    contas = listar_contas(con, logado.cliente_id)

    return {
        "cliente": formatar_cliente(cliente),
        "contas": [formatar_conta(conta) for conta in contas],
    }
