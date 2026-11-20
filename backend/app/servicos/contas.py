"""Regras das contas bancárias: listar, buscar e abrir conta nova."""

import secrets

from app import config
from app.banco import buscar_todos, buscar_um, executar
from app.erros import ErroApi

# Consulta base das contas de um cliente (só titularidades vigentes, sem data_fim).
SELECT_CONTAS = """
    SELECT c.*, a.codigo_agencia, a.digito AS digito_agencia,
           b.codigo_banco, t.tipo_titular
      FROM conta c
      JOIN agencia a ON a.id = c.agencia_id
      JOIN banco b ON b.id = a.banco_id
      JOIN titularidade t ON t.conta_id = c.id
     WHERE t.cliente_id = %s AND t.data_fim IS NULL
"""


def listar_contas(con, cliente_id):
    """Contas do cliente. A conta em que ele é TITULAR vem primeiro (é a "principal")."""
    return buscar_todos(
        con,
        SELECT_CONTAS + " ORDER BY t.tipo_titular = 'TITULAR' DESC, c.id",
        (cliente_id,),
    )


def _id_valido(valor):
    """Converte o id da URL em número positivo. Devolve None se não for válido."""
    texto_id = str(valor).strip()
    return int(texto_id) if texto_id.isdigit() and int(texto_id) > 0 else None


def buscar_conta_do_cliente(con, conta_id, cliente_id):
    """Busca uma conta garantindo que ela pertence ao cliente logado.

    Responde 404 (e não 403) de propósito: assim ninguém descobre,
    testando ids, quais contas existem e são de outras pessoas.
    """
    conta_id = _id_valido(conta_id)

    if conta_id is None:
        raise ErroApi(404, "Conta não encontrada.")

    conta = buscar_um(con, SELECT_CONTAS + " AND c.id = %s", (cliente_id, conta_id))

    if not conta:
        raise ErroApi(404, "Conta não encontrada.")

    return conta


def resolver_conta_origem(con, conta_id, cliente_id):
    """Devolve a conta pedida ou, se nenhuma foi pedida, a conta principal."""
    if conta_id not in (None, ""):
        return buscar_conta_do_cliente(con, conta_id, cliente_id)

    contas = listar_contas(con, cliente_id)

    if not contas:
        raise ErroApi(404, "Nenhuma conta encontrada para este cliente.")

    return contas[0]


def _buscar_agencia_padrao(con):
    """Agência configurada no .env (BANCO_CODIGO + AGENCIA_CODIGO)."""
    agencia = buscar_um(
        con,
        """SELECT a.id
             FROM agencia a
             JOIN banco b ON b.id = a.banco_id
            WHERE b.codigo_banco = %s AND a.codigo_agencia = %s
              AND a.status = 'ATIVA' AND b.status = 'ATIVO'""",
        (config.BANCO_CODIGO, config.AGENCIA_CODIGO),
    )

    if not agencia:
        # Erro de configuração do servidor (não do usuário): vira 500 e aparece no log.
        raise RuntimeError(
            f"Agência {config.AGENCIA_CODIGO} do banco {config.BANCO_CODIGO} não encontrada. "
            "Rode a seção 13 (DADOS INICIAIS) do SQL ou confira BANCO_CODIGO e AGENCIA_CODIGO no .env."
        )

    return agencia["id"]


def calcular_digito(numero):
    """Dígito verificador da conta (módulo 11, pesos de 2 a 9 da direita para a esquerda)."""
    soma = 0
    peso = 2

    for algarismo in reversed(numero):
        soma += int(algarismo) * peso
        peso = 2 if peso == 9 else peso + 1

    resto = 11 - (soma % 11)
    return "0" if resto >= 10 else str(resto)


def abrir_conta(con):
    """Abre uma conta DIGITAL na agência padrão, com número aleatório de 8 dígitos.

    Precisa ser chamada dentro de uma transação (junto com o cadastro do cliente).
    """
    agencia_id = _buscar_agencia_padrao(con)

    for _ in range(10):
        numero = str(10_000_000 + secrets.randbelow(90_000_000))

        if buscar_um(
            con,
            "SELECT id FROM conta WHERE agencia_id = %s AND numero_conta = %s",
            (agencia_id, numero),
        ):
            continue  # número já usado: sorteia outro

        conta_id, _ = executar(
            con,
            """INSERT INTO conta (agencia_id, numero_conta, digito, tipo_conta)
               VALUES (%s, %s, %s, 'DIGITAL')""",
            (agencia_id, numero, calcular_digito(numero)),
        )
        return conta_id

    raise RuntimeError("Não foi possível gerar um número de conta livre.")
