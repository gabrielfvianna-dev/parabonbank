const { ErroApi } = require("../utils/erros");

// Rota inexistente.
const rotaNaoEncontrada = (req, res) => {
  res.status(404).json({ message: "Rota não encontrada." });
};

// Tratamento central de erros. Sempre responde em JSON.
// eslint-disable-next-line no-unused-vars
const tratarErros = (erro, req, res, next) => {
  if (erro instanceof ErroApi) {
    const corpo = { message: erro.message };

    if (erro.errors) {
      corpo.errors = erro.errors;
    }

    return res.status(erro.status).json(corpo);
  }

  if (erro.type === "entity.parse.failed") {
    return res.status(400).json({ message: "JSON inválido." });
  }

  if (erro.type === "entity.too.large") {
    return res.status(413).json({ message: "Requisição muito grande." });
  }

  console.error("[erro]", erro);
  return res
    .status(500)
    .json({ message: "Erro interno. Tente novamente mais tarde." });
};

module.exports = { rotaNaoEncontrada, tratarErros };
