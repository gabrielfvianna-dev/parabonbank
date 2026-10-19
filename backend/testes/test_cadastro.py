"""Testes de POST /api/auth/cadastro (tela app/cadastro.js)."""

from apoio import dados_cadastro, gerar_cpf

MSG_SENHA = (
    "A senha deve ter 8–64 caracteres, com maiúscula, minúscula, número e caractere especial."
)
MSG_PIN = "O PIN deve ter 6 dígitos e não pode ser uma sequência ou repetição."


def test_cadastro_com_sucesso(api):
    dados = dados_cadastro(cpf=gerar_cpf(com_mascara=True), phone="(12) 99876-5432")
    resposta = api.post("/api/auth/cadastro", dados)

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    cliente = corpo["cliente"]
    conta = corpo["conta"]

    # Os nomes dos campos são os mesmos do frontend.
    assert cliente["fullName"] == dados["fullName"]
    assert cliente["cpf"] == "".join(c for c in dados["cpf"] if c.isdigit())
    assert cliente["birthDate"] == dados["birthDate"]
    assert cliente["email"] == dados["email"]
    assert cliente["phone"] == "12998765432"
    assert cliente["status"] == "ATIVO"

    # Uma conta digital é aberta automaticamente, com saldo zero.
    assert conta["accountType"] == "DIGITAL"
    assert conta["balance"] == 0
    assert conta["holderType"] == "TITULAR"
    assert conta["agency"] == "0001"
    assert len(conta["accountNumber"]) == 8

    # Nada de senha ou PIN na resposta.
    texto = resposta.text
    assert dados["password"] not in texto
    assert dados["pin"] not in texto


def test_corpo_vazio_retorna_erros_com_os_nomes_do_front(api):
    resposta = api.post("/api/auth/cadastro", {})

    assert resposta.status_code == 400
    erros = resposta.json()["errors"]
    assert set(erros) == {"fullName", "cpf", "birthDate", "email", "phone", "password", "pin", "terms"}
    assert erros["fullName"] == "Informe seu nome completo."
    assert erros["cpf"] == "Informe um CPF válido."
    assert erros["terms"] == "Aceite os termos para continuar."


def test_mensagens_iguais_as_do_front(api):
    dados = dados_cadastro(
        cpf="11111111111",
        birthDate="31-02-2000",
        email="email-invalido",
        phone="123",
        password="fraca",
        confirmPassword="diferente",
        pin="123456",
        confirmPin="000000",
        termsAccepted=False,
    )
    erros = api.post("/api/auth/cadastro", dados).json()["errors"]

    assert erros == {
        "cpf": "Informe um CPF válido.",
        "birthDate": "Informe uma data válida e tenha pelo menos 18 anos.",
        "email": "Informe um e-mail válido.",
        "phone": "Informe um telefone válido.",
        "password": MSG_SENHA,
        "confirmPassword": "As senhas não são iguais.",
        "pin": MSG_PIN,
        "confirmPin": "Os PINs não são iguais.",
        "terms": "Aceite os termos para continuar.",
    }


def test_menor_de_idade_nao_pode_cadastrar(api):
    resposta = api.post("/api/auth/cadastro", dados_cadastro(birthDate="01-01-2015"))

    assert resposta.status_code == 400
    assert "birthDate" in resposta.json()["errors"]


def test_pin_repetido_ou_sequencia(api):
    for pin in ("111111", "123456", "654321", "12345", "abcdef"):
        resposta = api.post("/api/auth/cadastro", dados_cadastro(pin=pin, confirmPin=pin))
        assert resposta.status_code == 400, pin
        assert resposta.json()["errors"] == {"pin": MSG_PIN}


def test_cpf_duplicado(api, usuario):
    resposta = api.post("/api/auth/cadastro", dados_cadastro(cpf=usuario["dados"]["cpf"]))

    assert resposta.status_code == 409
    assert resposta.json()["errors"] == {"cpf": "Este CPF já está cadastrado."}


def test_email_duplicado_ignora_maiusculas(api, usuario):
    email = usuario["dados"]["email"].upper()
    resposta = api.post("/api/auth/cadastro", dados_cadastro(email=email))

    assert resposta.status_code == 409
    assert resposta.json()["errors"] == {"email": "Este e-mail já está cadastrado."}


def test_tipos_errados_no_json_nao_quebram_a_api(api):
    resposta = api.post("/api/auth/cadastro", {"fullName": 123, "cpf": None, "termsAccepted": "sim"})

    assert resposta.status_code == 400
    assert "fullName" in resposta.json()["errors"]
    assert "terms" in resposta.json()["errors"]


def test_json_malformado(api):
    resposta = api.chamar(
        "POST",
        "/api/auth/cadastro",
        data="{nao é json",
        headers={"Content-Type": "application/json"},
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"message": "JSON inválido."}
