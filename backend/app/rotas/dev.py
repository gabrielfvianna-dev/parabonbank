"""ROTAS SOMENTE PARA DESENVOLVIMENTO E TESTES.

Só existem quando HABILITAR_ROTAS_DEV=true no .env.
Com "false", a rota nem é registrada: quem tentar chamar recebe 404.
"""

from fastapi import APIRouter, Depends

from app.autenticacao import UsuarioLogado, usuario_logado
from app.banco import buscar_um, conexao, executar, transacao
from app.erros import MSG_DADOS_INVALIDOS, ErroApi
from app.seguranca.http import corpo_json
from app.seguranca.tokens import gerar_uuid
from app.servicos.contas import buscar_conta_do_cliente
from app.utils.dinheiro import ler_valor
from app.utils.formatadores import formatar_conta

router = APIRouter()


# ------------------------------------------------------------
# POST /api/dev/contas/{id}/deposito — coloca saldo na conta para testar o Pix.
# Body: { "amount": 1000 }
# ------------------------------------------------------------
@router.post("/contas/{conta_id}/deposito", status_code=201)
def deposito_de_teste(
    conta_id: str,
    corpo: dict = Depends(corpo_json),
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    valor = ler_valor(corpo.get("amount"))

    if valor is None or valor <= 0:
        raise ErroApi(400, MSG_DADOS_INVALIDOS, {"amount": "Informe um valor válido."})

    conta = buscar_conta_do_cliente(con, conta_id, logado.cliente_id)

    with transacao(con):
        # Trava a conta para dois depósitos ao mesmo tempo não se atropelarem.
        travada = buscar_um(con, "SELECT saldo FROM conta WHERE id = %s FOR UPDATE", (conta["id"],))
        saldo_anterior = travada["saldo"]
        saldo_posterior = saldo_anterior + valor

        executar(
            con,
            """INSERT INTO transacao
                 (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
               VALUES (%s, 'DEPOSITO', %s, 'Depósito de teste', %s, %s, %s)""",
            (conta["id"], valor, saldo_anterior, saldo_posterior, gerar_uuid()),
        )
        executar(con, "UPDATE conta SET saldo = %s WHERE id = %s", (saldo_posterior, conta["id"]))

    atualizada = buscar_conta_do_cliente(con, conta["id"], logado.cliente_id)

    return {"message": "Depósito de teste realizado.", "conta": formatar_conta(atualizada)}
