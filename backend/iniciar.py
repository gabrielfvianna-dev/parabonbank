"""Inicia a API do Parabon Bank.

Uso (dentro da pasta backend, com o ambiente virtual ativado):

    python iniciar.py          → modo normal
    python iniciar.py --dev    → reinicia sozinho quando você salva um arquivo

"0.0.0.0" faz a API aceitar conexões da rede Wi-Fi, para o celular (Expo Go) conseguir chamar.
"""

import sys

import uvicorn

from app import config

if __name__ == "__main__":
    config.conferir_configuracao()

    opcoes = {}

    # Com certificado configurado no .env, a API só responde em https://.
    # Senha, token e dados bancários passam criptografados pela rede.
    if config.HTTPS_ATIVO:
        opcoes["ssl_certfile"] = config.caminho_arquivo(config.HTTPS_CERT)
        opcoes["ssl_keyfile"] = config.caminho_arquivo(config.HTTPS_KEY)

    protocolo = "https" if config.HTTPS_ATIVO else "http"
    print(f"API do Parabon Bank rodando em {protocolo}://localhost:{config.PORTA}")

    if not config.HTTPS_ATIVO:
        print("AVISO: HTTPS desligado. Os dados passam pela rede sem criptografia (veja docs/backend.md).")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.PORTA,
        reload="--dev" in sys.argv,
        # Não anuncia qual servidor está rodando (é informação útil para um atacante).
        server_header=False,
        # Não confia em cabeçalhos X-Forwarded-For: qualquer um poderia forjar o IP
        # e escapar do limite de tentativas.
        proxy_headers=False,
        **opcoes,
    )
