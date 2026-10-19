"""Testes de login, sessão e logout (tela app/login.js)."""

from apoio import SENHA_PADRAO

MSG_INVALIDO = "E-mail/CPF ou senha inválidos."


def test_login_por_email(api, usuario):
    resposta = api.post(
        "/api/auth/login",
        {"identifier": usuario["dados"]["email"], "password": SENHA_PADRAO},
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["tokenType"] == "Bearer"
    assert len(corpo["token"]) >= 40
    assert corpo["expiresAt"]
    assert corpo["cliente"]["email"] == usuario["dados"]["email"]


def test_login_por_cpf_com_mascara(api, usuario):
    cpf = usuario["dados"]["cpf"]
    mascara = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    resposta = api.post("/api/auth/login", {"identifier": mascara, "password": SENHA_PADRAO})

    assert resposta.status_code == 200, resposta.text


def test_campos_vazios(api):
    resposta = api.post("/api/auth/login", {"identifier": "  ", "password": ""})

    assert resposta.status_code == 400
    assert resposta.json()["errors"] == {
        "identifier": "Informe seu e-mail ou CPF.",
        "password": "Informe sua senha.",
    }


def test_senha_errada_e_usuario_inexistente_tem_a_mesma_resposta(api, usuario):
    errada = api.post(
        "/api/auth/login",
        {"identifier": usuario["dados"]["email"], "password": "Errada@123"},
    )
    inexistente = api.post(
        "/api/auth/login",
        {"identifier": "ninguem@parabon.test", "password": "Errada@123"},
    )

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"message": MSG_INVALIDO}


def test_bloqueio_apos_5_senhas_erradas(api, usuario):
    corpo = {"identifier": usuario["dados"]["email"], "password": "Errada@123"}

    for _ in range(4):
        assert api.post("/api/auth/login", corpo).status_code == 401

    quinta = api.post("/api/auth/login", corpo)
    assert quinta.status_code == 423

    # Mesmo com a senha certa, continua bloqueado.
    certa = api.post(
        "/api/auth/login",
        {"identifier": usuario["dados"]["email"], "password": SENHA_PADRAO},
    )
    assert certa.status_code == 423


def test_usuarios_de_exemplo_do_script_sql_nao_entram(api):
    # O script SQL grava um hash falso ("$2b$12$HASH_EXEMPLO...") para Maria e João.
    resposta = api.post(
        "/api/auth/login",
        {"identifier": "maria@email.com", "password": "qualquer"},
    )
    assert resposta.status_code in (401, 423)


def test_rota_protegida_exige_token(api):
    assert api.get("/api/clientes/me").status_code == 401
    assert api.get("/api/clientes/me", token="token-falso").status_code == 401


def test_me_retorna_cliente_e_contas(api, usuario):
    resposta = api.get("/api/clientes/me", token=usuario["token"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["cliente"]["id"] == usuario["cliente"]["id"]
    assert [c["id"] for c in corpo["contas"]] == [usuario["conta"]["id"]]


def test_logout_invalida_o_token(api, usuario):
    assert api.post("/api/auth/logout", token=usuario["token"]).status_code == 200

    depois = api.get("/api/clientes/me", token=usuario["token"])
    assert depois.status_code == 401


def test_rota_inexistente(api):
    resposta = api.get("/api/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"message": "Rota não encontrada."}
