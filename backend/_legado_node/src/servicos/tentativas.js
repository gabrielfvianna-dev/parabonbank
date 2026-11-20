const config = require("../config");
const { pool } = require("../db");

// Soma uma tentativa de senha errada em usuario_acesso.tentativas_login.
// Ao atingir o limite, bloqueia o acesso (bloqueado_ate) e zera o contador.
// Retorna true se o acesso acabou de ser bloqueado.
const registrarSenhaErrada = async (usuarioId) => {
  await pool.execute(
    `UPDATE usuario_acesso
        SET tentativas_login = tentativas_login + 1
      WHERE id = ?`,
    [usuarioId],
  );

  const [resultado] = await pool.execute(
    `UPDATE usuario_acesso
        SET bloqueado_ate = DATE_ADD(NOW(), INTERVAL ? MINUTE),
            tentativas_login = 0
      WHERE id = ? AND tentativas_login >= ?`,
    [config.loginBloqueioMinutos, usuarioId, config.loginMaxTentativas],
  );

  return resultado.affectedRows > 0;
};

// Zera o contador depois de uma senha correta.
const limparTentativas = async (usuarioId, executor = pool) => {
  await executor.execute(
    `UPDATE usuario_acesso
        SET tentativas_login = 0, bloqueado_ate = NULL
      WHERE id = ?`,
    [usuarioId],
  );
};

module.exports = { registrarSenhaErrada, limparTentativas };
