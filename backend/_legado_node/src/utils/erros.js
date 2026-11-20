// Erro padrão da API.
// Toda resposta de erro segue o formato:
// { "message": "texto para o usuário", "errors": { "campo": "mensagem" } }
// "errors" só aparece quando o erro é de um campo específico.
class ErroApi extends Error {
  constructor(status, message, errors) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

module.exports = { ErroApi };
