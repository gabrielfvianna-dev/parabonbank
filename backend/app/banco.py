"""Conexão com o MySQL.

Cada requisição recebe a sua própria conexão, que é fechada no final.
Todas as consultas usam parâmetros (%s): o valor digitado pelo usuário
NUNCA é colado dentro do texto do SQL. Isso impede SQL injection.
"""

from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from app import config


def abrir_conexao():
    """Abre uma conexão nova com o banco sistema_bancario."""
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        # Cada linha chega como dicionário: linha["nome_completo"].
        cursorclass=DictCursor,
        # Fora de uma transação, cada comando é confirmado na hora.
        autocommit=True,
        connect_timeout=5,
    )


class ConexaoSobDemanda:
    """Conexão que só é aberta no primeiro uso.

    Assim, uma requisição com campo vazio ou sem token é recusada
    sem nem tocar no banco: mais rápido e menos conexões abertas à toa.
    """

    def __init__(self):
        self._con = None

    def __getattr__(self, nome):
        # Chamado quando a rota usa con.cursor(), con.begin(), con.commit()...
        if self._con is None:
            self._con = abrir_conexao()

        return getattr(self._con, nome)

    def fechar(self):
        if self._con is not None:
            self._con.close()


def conexao():
    """Dependência do FastAPI: entrega uma conexão para a rota e fecha no final."""
    con = ConexaoSobDemanda()

    try:
        yield con
    finally:
        con.fechar()


@contextmanager
def transacao(con):
    """Agrupa vários comandos: ou TODOS são gravados, ou NENHUM.

    Uso:
        with transacao(con):
            ... vários INSERT/UPDATE ...

    Se acontecer qualquer erro no meio, tudo é desfeito (ROLLBACK).
    """
    con.begin()

    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise


def buscar_um(con, sql, parametros=()):
    """Executa um SELECT e devolve a primeira linha (ou None)."""
    with con.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchone()


def buscar_todos(con, sql, parametros=()):
    """Executa um SELECT e devolve todas as linhas."""
    with con.cursor() as cursor:
        cursor.execute(sql, parametros)
        return list(cursor.fetchall())


def executar(con, sql, parametros=()):
    """Executa um INSERT/UPDATE/DELETE.

    Devolve (id_inserido, linhas_afetadas).
    """
    with con.cursor() as cursor:
        linhas = cursor.execute(sql, parametros)
        return cursor.lastrowid, linhas
