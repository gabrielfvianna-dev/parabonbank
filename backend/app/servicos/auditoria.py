"""Registro de ações na tabela auditoria (quem fez o quê, quando, de qual IP e se deu certo)."""

import logging

from app.banco import executar

log = logging.getLogger("parabon.auditoria")


def registrar_auditoria(
    con,
    *,
    acao,
    entidade,
    resultado,
    cliente_id=None,
    usuario_id=None,
    entidade_id=None,
    ip=None,
    obrigatoria=False,
):
    """Grava um registro de auditoria.

    obrigatoria=True: usado dentro de transações (cadastro, login, Pix).
        Se a auditoria falhar, a operação inteira é desfeita. Nada acontece sem registro.
    obrigatoria=False: usado nos registros de FALHA.
        Se a auditoria falhar, só aparece no log; a resposta ao usuário continua a mesma.
    """
    try:
        executar(
            con,
            """INSERT INTO auditoria
                 (cliente_id, usuario_id, acao, entidade, entidade_id, ip, resultado)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (cliente_id, usuario_id, acao, entidade, entidade_id, ip, resultado),
        )
    except Exception as erro:
        if obrigatoria:
            raise

        log.error("falha ao registrar auditoria (%s): %s", acao, erro)
