const express = require("express");

const { pool } = require("../db");
const { autenticar } = require("../middlewares/autenticacao");
const {
  buscarContaDoCliente,
  listarContas,
} = require("../servicos/contas");
const { formatarConta, formatarTransacao } = require("../utils/formatadores");

const router = express.Router();

router.use(autenticar);

// GET /api/contas — todas as contas do cliente logado.
router.get("/", async (req, res) => {
  const contas = await listarContas(req.auth.clienteId);
  res.json({ contas: contas.map(formatarConta) });
});

// GET /api/contas/:id — uma conta (saldo atualizado).
router.get("/:id", async (req, res) => {
  const conta = await buscarContaDoCliente(req.params.id, req.auth.clienteId);
  res.json({ conta: formatarConta(conta) });
});

// GET /api/contas/:id/extrato?limit=50 — últimas transações da conta.
router.get("/:id/extrato", async (req, res) => {
  const conta = await buscarContaDoCliente(req.params.id, req.auth.clienteId);
  const limite = Math.min(Math.max(Number(req.query.limit) || 50, 1), 200);

  // LIMIT não aceita parâmetro "?" no execute; o valor já foi validado acima.
  const [transacoes] = await pool.execute(
    `SELECT * FROM transacao
      WHERE conta_id = ?
      ORDER BY data_hora DESC, id DESC
      LIMIT ${limite}`,
    [conta.id],
  );

  res.json({
    conta: formatarConta(conta),
    transacoes: transacoes.map(formatarTransacao),
  });
});

module.exports = router;
