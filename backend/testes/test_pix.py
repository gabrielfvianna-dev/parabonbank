"""Testes das chaves Pix e da API de envio (POST /api/pix/enviar)."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from apoio import SENHA_PADRAO


def criar_chave(api, usuario, tipo):
    resposta = api.post("/api/pix/chaves", {"keyType": tipo}, token=usuario["token"])
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["chave"]


def enviar(api, usuario, chave, valor, **extras):
    corpo = {"key": chave, "amount": valor, "password": SENHA_PADRAO, **extras}
    return api.post("/api/pix/enviar", corpo, token=usuario["token"])


# ------------------------------------------------------------------
# Chaves Pix
# ------------------------------------------------------------------


def test_cadastrar_todos_os_tipos_de_chave(api, usuario):
    dados = usuario["dados"]

    assert criar_chave(api, usuario, "CPF")["key"] == dados["cpf"]
    assert criar_chave(api, usuario, "EMAIL")["key"] == dados["email"]
    assert criar_chave(api, usuario, "TELEFONE")["key"] == f"+55{dados['phone']}"
    aleatoria = criar_chave(api, usuario, "ALEATORIA")
    assert len(aleatoria["key"]) == 36

    lista = api.get("/api/pix/chaves", token=usuario["token"]).json()["chaves"]
    assert {c["keyType"] for c in lista} == {"CPF", "EMAIL", "TELEFONE", "ALEATORIA"}


def test_chave_duplicada(api, usuario):
    criar_chave(api, usuario, "CPF")
    resposta = api.post("/api/pix/chaves", {"keyType": "CPF"}, token=usuario["token"])

    assert resposta.status_code == 409
    assert resposta.json()["errors"] == {"keyType": "Esta chave Pix já está cadastrada."}


def test_tipo_de_chave_invalido(api, usuario):
    resposta = api.post("/api/pix/chaves", {"keyType": "CNPJ"}, token=usuario["token"])
    assert resposta.status_code == 400
    assert "keyType" in resposta.json()["errors"]


def test_excluir_e_recadastrar_chave(api, usuario):
    chave = criar_chave(api, usuario, "EMAIL")

    excluir = api.delete(f"/api/pix/chaves/{chave['id']}", token=usuario["token"])
    assert excluir.status_code == 200
    assert api.get("/api/pix/chaves", token=usuario["token"]).json()["chaves"] == []

    de_novo = criar_chave(api, usuario, "EMAIL")
    assert de_novo["id"] == chave["id"]


def test_nao_exclui_chave_de_outra_pessoa(api, usuario, outro_usuario):
    chave = criar_chave(api, outro_usuario, "CPF")
    resposta = api.delete(f"/api/pix/chaves/{chave['id']}", token=usuario["token"])
    assert resposta.status_code == 404


# ------------------------------------------------------------------
# Envio de Pix
# ------------------------------------------------------------------


def test_pix_com_sucesso_movimenta_as_duas_contas(api, usuario, outro_usuario):
    api.depositar(usuario, 1000)
    criar_chave(api, outro_usuario, "EMAIL")

    resposta = enviar(api, usuario, outro_usuario["dados"]["email"], 150.75, description="Aluguel")

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    pix = corpo["pix"]
    assert pix["status"] == "CONCLUIDO"
    assert pix["amount"] == 150.75
    assert pix["description"] == "Aluguel"
    assert pix["endToEndId"].startswith("E00000999")
    assert len(pix["endToEndId"]) == 32
    assert pix["recipient"]["name"] == outro_usuario["dados"]["fullName"]
    assert corpo["conta"]["balance"] == 849.25

    assert api.saldo(usuario) == 849.25
    assert api.saldo(outro_usuario) == 150.75


def test_extrato_registra_saldo_antes_e_depois(api, usuario, outro_usuario):
    api.depositar(usuario, 200)
    criar_chave(api, outro_usuario, "CPF")
    assert enviar(api, usuario, outro_usuario["dados"]["cpf"], "50,00").status_code == 201

    extrato = api.get(
        f"/api/contas/{usuario['conta']['id']}/extrato", token=usuario["token"]
    ).json()["transacoes"]
    assert [t["type"] for t in extrato] == ["PIX_ENVIADO", "DEPOSITO"]
    assert extrato[0]["balanceBefore"] == 200
    assert extrato[0]["balanceAfter"] == 150

    recebido = api.get(
        f"/api/contas/{outro_usuario['conta']['id']}/extrato", token=outro_usuario["token"]
    ).json()["transacoes"]
    assert recebido[0]["type"] == "PIX_RECEBIDO"
    assert recebido[0]["amount"] == 50
    assert recebido[0]["balanceAfter"] == 50


def test_pix_por_telefone_digitado_sem_mascara(api, usuario, outro_usuario):
    api.depositar(usuario, 10)
    criar_chave(api, outro_usuario, "TELEFONE")

    resposta = enviar(api, usuario, outro_usuario["dados"]["phone"], 10)
    assert resposta.status_code == 201, resposta.text


def test_saldo_insuficiente(api, usuario, outro_usuario):
    api.depositar(usuario, 100)
    criar_chave(api, outro_usuario, "EMAIL")

    resposta = enviar(api, usuario, outro_usuario["dados"]["email"], 100.01)

    assert resposta.status_code == 422
    assert resposta.json()["errors"] == {"amount": "Saldo insuficiente."}
    assert api.saldo(usuario) == 100
    assert api.saldo(outro_usuario) == 0


def test_senha_errada_nao_envia(api, usuario, outro_usuario):
    api.depositar(usuario, 100)
    criar_chave(api, outro_usuario, "EMAIL")

    resposta = enviar(api, usuario, outro_usuario["dados"]["email"], 10, password="Errada@123")

    assert resposta.status_code == 401
    assert resposta.json()["errors"] == {"password": "Senha incorreta."}
    assert api.saldo(usuario) == 100


def test_chave_inexistente(api, usuario):
    api.depositar(usuario, 100)
    resposta = enviar(api, usuario, "naoexiste@parabon.test", 10)

    assert resposta.status_code == 404
    assert resposta.json()["errors"] == {"key": "Chave Pix não encontrada."}


def test_pix_para_a_propria_conta(api, usuario):
    api.depositar(usuario, 100)
    criar_chave(api, usuario, "CPF")

    resposta = enviar(api, usuario, usuario["dados"]["cpf"], 10)
    assert resposta.status_code == 400
    assert "key" in resposta.json()["errors"]


@pytest.mark.parametrize("valor", [0, -5, "abc", 10.555, None, "1e3"])
def test_valores_invalidos(api, usuario, valor):
    resposta = enviar(api, usuario, "qualquer@parabon.test", valor)
    assert resposta.status_code == 400
    assert resposta.json()["errors"]["amount"] == "Informe um valor válido."


def test_valor_acima_do_limite(api, usuario):
    resposta = enviar(api, usuario, "qualquer@parabon.test", 10000.01)
    assert resposta.status_code == 400
    assert resposta.json()["errors"]["amount"].startswith("O valor máximo por Pix")


def test_campos_obrigatorios(api, usuario):
    resposta = api.post("/api/pix/enviar", {}, token=usuario["token"])
    assert resposta.status_code == 400
    assert set(resposta.json()["errors"]) == {"key", "amount", "password"}


def test_pix_exige_login(api):
    resposta = api.post("/api/pix/enviar", {"key": "x", "amount": 1, "password": "x"})
    assert resposta.status_code == 401


def test_nao_ve_conta_de_outra_pessoa(api, usuario, outro_usuario):
    conta_alheia = outro_usuario["conta"]["id"]

    assert api.get(f"/api/contas/{conta_alheia}", token=usuario["token"]).status_code == 404
    assert api.get(f"/api/contas/{conta_alheia}/extrato", token=usuario["token"]).status_code == 404

    # Também não pode enviar Pix a partir da conta de outra pessoa.
    criar_chave(api, usuario, "EMAIL")
    resposta = enviar(api, outro_usuario, usuario["dados"]["email"], 1, accountId=usuario["conta"]["id"])
    assert resposta.status_code == 404


def test_pix_simultaneos_nao_gastam_mais_que_o_saldo(api, usuario, outro_usuario):
    """10 envios de R$ 100 ao mesmo tempo com saldo de R$ 500: só 5 podem passar."""
    api.depositar(usuario, 500)
    criar_chave(api, outro_usuario, "EMAIL")

    with ThreadPoolExecutor(max_workers=10) as executor:
        respostas = list(
            executor.map(
                lambda _: enviar(api, usuario, outro_usuario["dados"]["email"], 100),
                range(10),
            )
        )

    codigos = sorted(r.status_code for r in respostas)
    assert codigos == [201] * 5 + [422] * 5
    assert api.saldo(usuario) == 0
    assert api.saldo(outro_usuario) == 500
