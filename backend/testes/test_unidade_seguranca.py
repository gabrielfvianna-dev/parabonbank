"""Testes de unidade: rodam SEM a API e SEM o MySQL.

Conferem as peças de segurança isoladas (hash de senha, token, validações, dinheiro).
Rodar só estes:  python -m pytest testes/test_unidade_seguranca.py -v
"""

import hashlib
import sys
from decimal import Decimal
from pathlib import Path

import bcrypt
import pytest

# Deixa o pacote "app" (backend/app) importável a partir da pasta testes.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.seguranca import senhas, tokens  # noqa: E402
from app.utils.dinheiro import ler_valor  # noqa: E402
from app.validacoes import validar_cadastro, validar_cpf, validar_pin, validar_senha  # noqa: E402

SENHA = "Senha@123"


# ---------------- Senhas ----------------


def test_hash_e_argon2id_e_nao_contem_a_senha():
    hash_ = senhas.gerar_hash_senha(SENHA)
    assert hash_.startswith("$argon2id$")
    assert SENHA not in hash_


def test_mesma_senha_gera_hashes_diferentes():
    # Cada hash tem um "sal" aleatório: duas pessoas com a mesma senha têm hashes diferentes.
    assert senhas.gerar_hash_senha(SENHA) != senhas.gerar_hash_senha(SENHA)


def test_confere_senha_certa_e_errada():
    hash_ = senhas.gerar_hash_senha(SENHA)
    assert senhas.conferir_senha(SENHA, hash_) == (True, False)
    assert senhas.conferir_senha("Senha@124", hash_) == (False, False)


def test_sem_a_pimenta_certa_o_hash_nao_serve(monkeypatch):
    hash_ = senhas.gerar_hash_senha(SENHA)
    monkeypatch.setattr(config, "SENHA_PEPPER", "outra-pimenta-" + "x" * 40)
    assert senhas.conferir_senha(SENHA, hash_)[0] is False


def test_hash_antigo_bcrypt_entra_e_pede_atualizacao():
    hash_node = bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt(rounds=4)).decode()
    assert senhas.conferir_senha(SENHA, hash_node) == (True, True)
    assert senhas.conferir_senha("errada", hash_node) == (False, False)


def test_hash_falso_do_script_sql_nunca_entra():
    assert senhas.conferir_senha(SENHA, "$2b$12$HASH_EXEMPLO_NAO_USAR_EM_PRODUCAO")[0] is False


@pytest.mark.parametrize("valor", [None, "", 123, "A" * 129])
def test_senha_vazia_ou_gigante_nao_entra(valor):
    hash_ = senhas.gerar_hash_senha(SENHA)
    assert senhas.conferir_senha(valor, hash_)[0] is False


# ---------------- Tokens ----------------


def test_token_tem_256_bits_e_so_o_sha256_vai_para_o_banco():
    token = tokens.gerar_token_sessao()
    assert tokens.token_parece_valido(token)
    assert tokens.hash_token(token) == hashlib.sha256(token.encode()).hexdigest()
    assert token != tokens.gerar_token_sessao()


@pytest.mark.parametrize("token", ["", "token-falso", "a" * 42, "a" * 44, "a" * 42 + "!"])
def test_token_com_formato_errado_e_recusado(token):
    assert not tokens.token_parece_valido(token)


# ---------------- Validações ----------------


def test_cpf():
    assert validar_cpf("529.982.247-25")
    assert not validar_cpf("529.982.247-26")
    assert not validar_cpf("111.111.111-11")


def test_pin_e_senha():
    assert validar_pin("482915")
    assert not validar_pin("123456") and not validar_pin("111111") and not validar_pin("12a456")
    assert validar_senha(SENHA)
    assert not validar_senha("semnumero@A") and not validar_senha("Curta@1")


def test_cadastro_vazio_retorna_os_campos_do_front():
    assert set(validar_cadastro({})) == {
        "fullName", "cpf", "birthDate", "email", "phone", "password", "pin", "terms"
    }


def test_termos_so_aceitam_true_de_verdade():
    assert "terms" in validar_cadastro({"termsAccepted": 1})
    assert "terms" in validar_cadastro({"termsAccepted": "true"})


# ---------------- Dinheiro ----------------


@pytest.mark.parametrize(
    "entrada, esperado",
    [(50.25, "50.25"), ("50,25", "50.25"), ("10", "10.00"), (1000, "1000.00")],
)
def test_valores_aceitos(entrada, esperado):
    assert ler_valor(entrada) == Decimal(esperado)


@pytest.mark.parametrize("entrada", [-1, "-1", "10.123", "abc", True, None, float("nan"), [10]])
def test_valores_recusados(entrada):
    assert ler_valor(entrada) is None
