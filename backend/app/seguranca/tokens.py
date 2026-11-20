"""Tokens de sessão e identificadores únicos.

Como funciona o token de login:
- A API sorteia 32 bytes (256 bits) com o gerador seguro do sistema (módulo secrets).
- O token vai UMA vez para o app, que guarda no SecureStore do celular.
- No banco (sessao.token_hash) fica só o SHA-256 do token.
  Se o banco vazar, quem pegar os hashes não consegue usá-los para entrar.
"""

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timezone

from app import config

# secrets.token_urlsafe(32) sempre gera 43 caracteres desse alfabeto.
_FORMATO_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


def gerar_token_sessao():
    """Token entregue ao app depois do login."""
    return secrets.token_urlsafe(32)


def hash_token(token):
    """SHA-256 do token, que é o que fica gravado em sessao.token_hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_parece_valido(token):
    """Descarta na hora tokens com formato errado, sem nem consultar o banco."""
    return bool(_FORMATO_TOKEN.fullmatch(token or ""))


def gerar_uuid():
    """Identificador único para transacao.identificador e chaves Pix aleatórias."""
    return str(uuid.uuid4())


def gerar_end_to_end_id():
    """Identificador do Pix no padrão E + ISPB(8) + AAAAMMDDHHmm + 11 caracteres."""
    ispb = config.BANCO_CODIGO.zfill(8)[-8:]
    data = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    sufixo = "".join(secrets.choice(alfabeto) for _ in range(11))
    return f"E{ispb}{data}{sufixo}"
