"""Hash e conferência de senhas.

Como a senha é guardada (coluna usuario_acesso.senha_hash):

    senha digitada
        │  1) HMAC-SHA256 com a SENHA_PEPPER (chave secreta que só o servidor tem)
        ▼
    "senha temperada"
        │  2) Argon2id (algoritmo lento de propósito, com "sal" aleatório)
        ▼
    $argon2id$v=19$m=65536,t=3,p=4$...   ← é ISSO que vai para o banco

Por que duas etapas?
- O Argon2id é lento e gasta memória de propósito: quem roubar o banco
  levaria anos para testar senhas, mesmo com placa de vídeo.
- A pimenta (pepper) não fica no banco. Sem ela, o hash roubado sozinho
  não serve nem para começar a adivinhar.

A senha em texto puro nunca é gravada, nunca aparece em log e nunca volta na resposta.
"""

import base64
import hashlib
import hmac

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app import config

# Argon2id com os parâmetros recomendados pela RFC 9106 (64 MiB de memória, 3 passadas).
_argon2 = PasswordHasher()

# Senhas maiores que isso nem são processadas: evita que alguém mande
# um texto gigante só para deixar o servidor lento calculando hash.
TAMANHO_MAXIMO = 128


def _temperar(senha):
    """Mistura a senha com a pimenta secreta (HMAC-SHA256)."""
    resumo = hmac.new(
        config.SENHA_PEPPER.encode("utf-8"),
        senha.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(resumo)


# Hash "de mentira", usado quando o e-mail/CPF não existe.
# Assim o login demora o mesmo tempo nos dois casos e ninguém descobre,
# pelo tempo de resposta, quais e-mails têm conta no banco.
_HASH_FALSO = _argon2.hash(b"parabon-hash-falso")


def _gastar_tempo_igual(senha):
    try:
        _argon2.verify(_HASH_FALSO, _temperar(senha[:TAMANHO_MAXIMO]))
    except VerificationError:
        pass


def gerar_hash_senha(senha):
    """Gera o hash que será gravado em usuario_acesso.senha_hash."""
    return _argon2.hash(_temperar(senha))


def conferir_senha(senha, hash_salvo):
    """Confere a senha digitada com o hash do banco.

    Devolve (senha_correta, precisa_atualizar_hash).

    "precisa_atualizar_hash" fica True quando o hash é de um formato antigo
    (bcrypt, criado pelo backend em Node) ou com parâmetros mais fracos.
    Nesse caso, a rota de login grava um hash novo, já em Argon2id.
    """
    if not isinstance(senha, str) or not senha or len(senha) > TAMANHO_MAXIMO:
        _gastar_tempo_igual(senha if isinstance(senha, str) else "")
        return False, False

    hash_salvo = hash_salvo or ""

    # Formato atual: Argon2id + pimenta.
    if hash_salvo.startswith("$argon2"):
        try:
            _argon2.verify(hash_salvo, _temperar(senha))
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False, False

        return True, _argon2.check_needs_rehash(hash_salvo)

    # Formato antigo: bcrypt (contas criadas pelo backend em Node).
    # Se a senha estiver certa, o hash é trocado por Argon2id no mesmo login.
    if hash_salvo.startswith("$2"):
        try:
            correta = bcrypt.checkpw(senha.encode("utf-8"), hash_salvo.encode("utf-8"))
        except ValueError:
            # Hash inválido, como os de exemplo do script SQL ("$2b$12$HASH_EXEMPLO...").
            correta = False

        return correta, correta

    # Qualquer outra coisa (usuário inexistente, hash vazio ou estranho): nunca entra,
    # mas gasta o mesmo tempo de uma conferência de verdade.
    _gastar_tempo_igual(senha)
    return False, False
