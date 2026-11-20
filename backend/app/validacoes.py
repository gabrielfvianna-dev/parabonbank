"""Validações do backend.

As regras e as mensagens são as MESMAS do frontend (app/cadastro.js),
e os erros usam os MESMOS nomes de campo (fullName, cpf, birthDate...),
para que o app possa fazer setErrors(resposta.errors) diretamente.

O backend valida de novo mesmo o front já tendo validado: qualquer pessoa
pode chamar a API sem passar pelo app, então o servidor nunca confia no que chega.
"""

import re
from datetime import date

MENSAGENS = {
    "fullName": "Informe seu nome completo.",
    "cpf": "Informe um CPF válido.",
    "birthDate": "Informe uma data válida e tenha pelo menos 18 anos.",
    "email": "Informe um e-mail válido.",
    "phone": "Informe um telefone válido.",
    "password": (
        "A senha deve ter 8–64 caracteres, com maiúscula, minúscula, "
        "número e caractere especial."
    ),
    "confirmPassword": "As senhas não são iguais.",
    "pin": "O PIN deve ter 6 dígitos e não pode ser uma sequência ou repetição.",
    "confirmPin": "Os PINs não são iguais.",
    "terms": "Aceite os termos para continuar.",
}

# Usamos [0-9] e não \d: no Python, \d também aceita dígitos de outros alfabetos (ex.: "٣").
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_DATA_APP = re.compile(r"[0-9]{2}-[0-9]{2}-[0-9]{4}")
_PIN = re.compile(r"[0-9]{6}")


def texto(valor):
    """Garante que o valor seja texto (o JSON pode trazer número, lista, null...)."""
    return valor if isinstance(valor, str) else ""


def only_numbers(valor):
    """Remove tudo que não for número (tira a máscara de CPF e telefone)."""
    return re.sub(r"[^0-9]", "", texto(valor))


def validar_cpf(valor):
    """Valida o CPF pelos dois dígitos verificadores."""
    numeros = only_numbers(valor)

    if len(numeros) != 11 or len(set(numeros)) == 1:
        return False

    for tamanho in (9, 10):
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        resto = (soma * 10) % 11

        if resto == 10:
            resto = 0

        if resto != int(numeros[tamanho]):
            return False

    return True


def validar_email(valor):
    """Formato básico de e-mail, com no máximo 150 caracteres (tamanho da coluna)."""
    email = texto(valor)
    return len(email) <= 150 and bool(_EMAIL.fullmatch(email))


def data_app_para_date(valor):
    """Converte "DD-MM-AAAA" (formato do app) para date. Devolve None se a data não existir."""
    data = texto(valor)

    if not _DATA_APP.fullmatch(data):
        return None

    dia, mes, ano = (int(parte) for parte in data.split("-"))

    try:
        return date(ano, mes, dia)
    except ValueError:  # ex.: 31-02-2000
        return None


def validar_nascimento(valor):
    """Data válida, a partir de 1900, e pelo menos 18 anos completos."""
    nascimento = data_app_para_date(valor)

    if not nascimento or nascimento.year < 1900:
        return False

    hoje = date.today()
    idade = hoje.year - nascimento.year

    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        idade -= 1

    return idade >= 18


def validar_telefone(valor):
    """Telefone brasileiro com DDD: 10 ou 11 dígitos."""
    return len(only_numbers(valor)) in (10, 11)


def validar_senha(valor):
    """8 a 64 caracteres, com maiúscula, minúscula, número e caractere especial."""
    senha = texto(valor)

    if not 8 <= len(senha) <= 64:
        return False

    return all(
        (
            re.search(r"[A-Z]", senha),
            re.search(r"[a-z]", senha),
            re.search(r"[0-9]", senha),
            re.search(r"[^A-Za-z0-9]", senha),
        )
    )


def validar_pin(valor):
    """6 dígitos, sem repetição (111111) e sem sequência (123456 / 654321)."""
    pin = texto(valor)

    if not _PIN.fullmatch(pin) or len(set(pin)) == 1:
        return False

    return pin not in ("123456", "654321")


def validar_cadastro(corpo):
    """Valida todos os campos da tela de cadastro.

    Devolve um dicionário { campo: mensagem }, vazio quando está tudo certo.
    """
    erros = {}
    nome = texto(corpo.get("fullName")).strip()

    if not 3 <= len(nome) <= 150:
        erros["fullName"] = MENSAGENS["fullName"]

    if not validar_cpf(corpo.get("cpf")):
        erros["cpf"] = MENSAGENS["cpf"]

    if not validar_nascimento(corpo.get("birthDate")):
        erros["birthDate"] = MENSAGENS["birthDate"]

    if not validar_email(texto(corpo.get("email")).strip()):
        erros["email"] = MENSAGENS["email"]

    if not validar_telefone(corpo.get("phone")):
        erros["phone"] = MENSAGENS["phone"]

    if not validar_senha(corpo.get("password")):
        erros["password"] = MENSAGENS["password"]

    if texto(corpo.get("password")) != texto(corpo.get("confirmPassword")):
        erros["confirmPassword"] = MENSAGENS["confirmPassword"]

    if not validar_pin(corpo.get("pin")):
        erros["pin"] = MENSAGENS["pin"]

    if texto(corpo.get("pin")) != texto(corpo.get("confirmPin")):
        erros["confirmPin"] = MENSAGENS["confirmPin"]

    # Só aceita o booleano true do JSON (1, "true", "sim"... não valem).
    if corpo.get("termsAccepted") is not True:
        erros["terms"] = MENSAGENS["terms"]

    return erros
