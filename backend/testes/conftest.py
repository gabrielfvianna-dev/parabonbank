import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apoio import BASE_URL, ENV, Api  # noqa: E402


@pytest.fixture(scope="session")
def api():
    """Cliente da API. Para os testes com uma mensagem clara se a API estiver fora do ar."""
    try:
        resposta = requests.get(f"{BASE_URL}/api/health", timeout=5)
    except requests.RequestException:
        pytest.exit(
            f"A API não está respondendo em {BASE_URL}. Rode 'npm start' na pasta backend.",
            returncode=1,
        )

    if resposta.status_code != 200:
        pytest.exit(f"A API está no ar, mas sem banco: {resposta.text}", returncode=1)

    return Api()


@pytest.fixture
def usuario(api):
    return api.criar_usuario()


@pytest.fixture
def outro_usuario(api):
    return api.criar_usuario()


@pytest.fixture(scope="session")
def banco():
    """Conexão direta com o MySQL (somente leitura nos testes de criptografia)."""
    pymysql = pytest.importorskip("pymysql")

    if "DB_PASSWORD" not in ENV and "DB_USER" not in ENV:
        pytest.skip("Configure o backend/.env para os testes que leem o banco.")

    conexao = pymysql.connect(
        host=ENV.get("DB_HOST", "localhost"),
        port=int(ENV.get("DB_PORT", 3306)),
        user=ENV.get("DB_USER", "root"),
        password=ENV.get("DB_PASSWORD", ""),
        database=ENV.get("DB_NAME", "sistema_bancario"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    yield conexao
    conexao.close()
