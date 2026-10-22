"""Confere direto no MySQL que senhas e tokens NÃO ficam gravados em texto puro.

Precisa do backend/.env configurado (DB_USER, DB_PASSWORD...) e do PyMySQL.
Os testes só LEEM o banco.
"""

import hashlib

from apoio import SENHA_PADRAO


def test_senha_gravada_como_hash_bcrypt(api, banco, usuario):
    with banco.cursor() as cursor:
        cursor.execute(
            "SELECT senha_hash FROM usuario_acesso WHERE cliente_id = %s",
            (usuario["cliente"]["id"],),
        )
        senha_hash = cursor.fetchone()["senha_hash"]

    assert senha_hash.startswith("$2b$12$")
    assert SENHA_PADRAO not in senha_hash
    assert len(senha_hash) == 60


def test_token_gravado_somente_como_sha256(api, banco, usuario):
    token = usuario["token"]

    with banco.cursor() as cursor:
        cursor.execute(
            "SELECT token_hash FROM sessao WHERE cliente_id = %s",
            (usuario["cliente"]["id"],),
        )
        hashes = [linha["token_hash"] for linha in cursor.fetchall()]

    assert hashlib.sha256(token.encode()).hexdigest() in hashes
    assert token not in hashes


def test_pin_nao_e_gravado_em_lugar_nenhum(api, banco, usuario):
    pin = usuario["dados"]["pin"]

    with banco.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM cliente WHERE id = %s",
            (usuario["cliente"]["id"],),
        )
        cliente = cursor.fetchone()

    assert pin not in " ".join(str(valor) for valor in cliente.values())


def test_auditoria_registra_cadastro_aceite_e_login(api, banco, usuario):
    with banco.cursor() as cursor:
        cursor.execute(
            "SELECT acao, resultado FROM auditoria WHERE cliente_id = %s ORDER BY id",
            (usuario["cliente"]["id"],),
        )
        acoes = [(linha["acao"], linha["resultado"]) for linha in cursor.fetchall()]

    assert ("CADASTRO", "SUCESSO") in acoes
    assert ("ACEITE_TERMOS", "SUCESSO") in acoes
    assert ("LOGIN", "SUCESSO") in acoes
