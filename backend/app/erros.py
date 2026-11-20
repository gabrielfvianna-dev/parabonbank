"""Erro padrão da API.

Toda resposta de erro segue o mesmo formato, que é o que o frontend lê:

    { "message": "texto para o usuário", "errors": { "campo": "mensagem" } }

"errors" só aparece quando o erro é de um campo específico.
Os nomes dos campos são os mesmos das telas (fullName, cpf, password...).
"""


class ErroApi(Exception):
    def __init__(self, status, message, errors=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.errors = errors
        self.headers = headers

    def corpo(self):
        """Monta o JSON que vai para o app."""
        corpo = {"message": self.message}

        if self.errors:
            corpo["errors"] = self.errors

        return corpo


# Mensagens repetidas em vários lugares ficam aqui, para não ter versões diferentes.
MSG_DADOS_INVALIDOS = "Verifique os dados informados."
MSG_BLOQUEADO = (
    "Acesso bloqueado temporariamente por excesso de tentativas. "
    "Tente novamente mais tarde."
)
