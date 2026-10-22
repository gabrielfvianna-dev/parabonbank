const { pool } = require("../db");

// Grava um registro na tabela auditoria.
// "executor" pode ser o pool ou uma conexão dentro de uma transação.
// Falhas na auditoria não derrubam a requisição: apenas são exibidas no log.
const registrarAuditoria = async (
  {
    clienteId = null,
    usuarioId = null,
    acao,
    entidade,
    entidadeId = null,
    ip = null,
    resultado,
  },
  executor = pool,
) => {
  try {
    await executor.execute(
      `INSERT INTO auditoria
         (cliente_id, usuario_id, acao, entidade, entidade_id, ip, resultado)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        clienteId,
        usuarioId,
        acao,
        entidade,
        entidadeId,
        ip ? String(ip).slice(0, 45) : null,
        resultado,
      ],
    );
  } catch (erro) {
    // Dentro de uma transação o erro precisa subir para desfazer tudo.
    if (executor !== pool) {
      throw erro;
    }

    console.error("[auditoria] falha ao registrar:", erro.message);
  }
};

module.exports = { registrarAuditoria };
