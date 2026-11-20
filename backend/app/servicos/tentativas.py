"""Contador de senhas erradas e bloqueio temporário do acesso.

Depois de LOGIN_MAX_TENTATIVAS erros seguidos (padrão 5), o acesso fica bloqueado
por LOGIN_BLOQUEIO_MINUTOS (padrão 15), mesmo que a pessoa acerte a senha depois.
O mesmo contador vale para o login e para a confirmação de senha do Pix.
"""

from app import config
from app.banco import buscar_um, executar, transacao


def registrar_senha_errada(con, usuario_id):
    """Soma uma tentativa errada. Devolve True se o acesso acabou de ser bloqueado.

    A linha do usuário é travada (FOR UPDATE) enquanto contamos.
    Sem isso, várias tentativas enviadas ao MESMO tempo poderiam ler o mesmo
    número e "furar" o limite de 5.
    """
    with transacao(con):
        linha = buscar_um(
            con,
            "SELECT tentativas_login FROM usuario_acesso WHERE id = %s FOR UPDATE",
            (usuario_id,),
        )
        tentativas = int(linha["tentativas_login"]) + 1

        if tentativas >= config.LOGIN_MAX_TENTATIVAS:
            executar(
                con,
                """UPDATE usuario_acesso
                      SET tentativas_login = 0,
                          bloqueado_ate = DATE_ADD(NOW(), INTERVAL %s MINUTE)
                    WHERE id = %s""",
                (config.LOGIN_BLOQUEIO_MINUTOS, usuario_id),
            )
            return True

        executar(
            con,
            "UPDATE usuario_acesso SET tentativas_login = %s WHERE id = %s",
            (tentativas, usuario_id),
        )
        return False


def limpar_tentativas(con, usuario_id):
    """Zera o contador depois de uma senha correta."""
    executar(
        con,
        """UPDATE usuario_acesso
              SET tentativas_login = 0, bloqueado_ate = NULL
            WHERE id = %s""",
        (usuario_id,),
    )
