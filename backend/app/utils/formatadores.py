"""Transformam as linhas do banco no JSON que o app entende.

O banco usa nomes em português (nome_completo, numero_conta...) e o app usa
os nomes das telas (fullName, accountNumber...). Esta é a "tradução".

IMPORTANTE: só os campos listados aqui saem da API.
senha_hash, token_hash e outras colunas internas NUNCA aparecem nas respostas.
"""

from datetime import date, datetime

from app.utils.dinheiro import para_numero


def data_para_app(valor):
    """date do MySQL → "DD-MM-AAAA" (formato usado no app)."""
    if not valor:
        return None

    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d-%m-%Y")

    ano, mes, dia = str(valor)[:10].split("-")
    return f"{dia}-{mes}-{ano}"


def data_hora_para_app(valor):
    """datetime do MySQL → "AAAA-MM-DDTHH:MM:SS" (ISO 8601)."""
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%dT%H:%M:%S")

    return str(valor).replace(" ", "T")


def formatar_cliente(cliente):
    """Linha da tabela cliente → JSON do app."""
    return {
        "id": int(cliente["id"]),
        "fullName": cliente["nome_completo"],
        "socialName": cliente["nome_social"],
        "cpf": cliente["cpf"],
        "birthDate": data_para_app(cliente["data_nascimento"]),
        "email": cliente["email"],
        "phone": cliente["telefone"],
        "status": cliente["status"],
        "createdAt": data_hora_para_app(cliente["data_cadastro"]),
        "lastAccessAt": data_hora_para_app(cliente["ultimo_acesso"]),
    }


def formatar_conta(conta):
    """Linha da tabela conta (com dados da agência e do banco) → JSON do app."""
    return {
        "id": int(conta["id"]),
        "bankCode": conta["codigo_banco"],
        "agency": conta["codigo_agencia"],
        "agencyDigit": conta["digito_agencia"],
        "accountNumber": conta["numero_conta"],
        "accountDigit": conta["digito"],
        "accountType": conta["tipo_conta"],
        "balance": para_numero(conta["saldo"]),
        "overdraftLimit": para_numero(conta["limite_cheque_especial"]),
        "status": conta["status"],
        "holderType": conta["tipo_titular"],
        "openedAt": data_hora_para_app(conta["data_abertura"]),
    }


def formatar_transacao(transacao):
    """Linha da tabela transacao → JSON do app (usado no extrato do dashboard)."""
    return {
        "id": int(transacao["id"]),
        "type": transacao["tipo"],
        "amount": para_numero(transacao["valor"]),
        "description": transacao["descricao"],
        "balanceBefore": para_numero(transacao["saldo_anterior"]),
        "balanceAfter": para_numero(transacao["saldo_posterior"]),
        "status": transacao["status"],
        "identifier": transacao["identificador"],
        "dateTime": data_hora_para_app(transacao["data_hora"]),
    }


def formatar_chave_pix(chave):
    """Linha da tabela chave_pix → JSON do app."""
    return {
        "id": int(chave["id"]),
        "accountId": int(chave["conta_id"]),
        "keyType": chave["tipo_chave"],
        "key": chave["chave"],
        "status": chave["status"],
        "createdAt": data_hora_para_app(chave["criada_em"]),
    }
