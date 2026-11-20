"""Limite de requisições por IP (proteção contra força bruta e abuso).

Exemplo: no máximo 20 tentativas de login/cadastro a cada 15 minutos por IP.
Passou disso, a API responde 429 e avisa quantos segundos esperar (Retry-After).

Os contadores ficam na memória do servidor: zeram quando a API reinicia.
Para um único servidor (como no projeto) isso é suficiente.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.erros import ErroApi


class LimiteDeRequisicoes:
    def __init__(self, maximo, janela_segundos, mensagem):
        self.maximo = maximo
        self.janela = janela_segundos
        self.mensagem = mensagem
        # Para cada IP, a lista dos horários das últimas requisições.
        self._acessos = defaultdict(deque)
        # A API atende várias requisições ao mesmo tempo; a trava evita bagunça na contagem.
        self._trava = threading.Lock()

    def __call__(self, request: Request):
        """Usado como dependência do FastAPI: roda antes da rota."""
        ip = request.client.host if request.client else "desconhecido"
        agora = time.monotonic()

        with self._trava:
            acessos = self._acessos[ip]

            # Esquece as requisições que já saíram da janela de tempo.
            while acessos and acessos[0] <= agora - self.janela:
                acessos.popleft()

            if len(acessos) >= self.maximo:
                espera = int(acessos[0] + self.janela - agora) + 1
                raise ErroApi(429, self.mensagem, headers={"Retry-After": str(espera)})

            acessos.append(agora)

            # De vez em quando, apaga IPs que não aparecem há tempo (economiza memória).
            if len(self._acessos) > 10_000:
                for chave in [k for k, v in self._acessos.items() if not v]:
                    del self._acessos[chave]
