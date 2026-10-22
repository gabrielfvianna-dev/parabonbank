const { pool } = require("../db");
const { hashToken } = require("../seguranca/criptografia");
const { ErroApi } = require("../utils/erros");

// Protege as rotas que exigem login.
// O app deve enviar o header:  Authorization: Bearer <token>
const autenticar = async (req, res, next) => {
  const [tipo, token] = (req.get("authorization") || "").split(" ");

  if (tipo !== "Bearer" || !token) {
    throw new ErroApi(401, "Faça login para continuar.");
  }

  // O banco guarda apenas o hash do token.
  const [sessoes] = await pool.execute(
    `SELECT s.id AS sessao_id, s.cliente_id, s.expiracao <= NOW() AS expirada,
            cl.status AS cliente_status, ua.id AS usuario_id,
            ua.status AS usuario_status
       FROM sessao s
       JOIN cliente cl ON cl.id = s.cliente_id
       JOIN usuario_acesso ua ON ua.cliente_id = cl.id
      WHERE s.token_hash = ? AND s.status = 'ATIVA'`,
    [hashToken(token)],
  );

  if (sessoes.length === 0) {
    throw new ErroApi(401, "Sessão inválida. Faça login novamente.");
  }

  const sessao = sessoes[0];

  if (Number(sessao.expirada) === 1) {
    await pool.execute("UPDATE sessao SET status = 'EXPIRADA' WHERE id = ?", [
      sessao.sessao_id,
    ]);
    throw new ErroApi(401, "Sessão expirada. Faça login novamente.");
  }

  if (sessao.cliente_status !== "ATIVO" || sessao.usuario_status !== "ATIVO") {
    throw new ErroApi(403, "Acesso não permitido. Entre em contato com o banco.");
  }

  req.auth = {
    sessaoId: Number(sessao.sessao_id),
    clienteId: Number(sessao.cliente_id),
    usuarioId: Number(sessao.usuario_id),
  };

  next();
};

module.exports = { autenticar };
