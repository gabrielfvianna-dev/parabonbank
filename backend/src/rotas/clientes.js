const express = require("express");

const { pool } = require("../db");
const { autenticar } = require("../middlewares/autenticacao");
const { listarContas } = require("../servicos/contas");
const { formatarCliente, formatarConta } = require("../utils/formatadores");

const router = express.Router();

router.use(autenticar);

// GET /api/clientes/me — dados do cliente logado e suas contas.
router.get("/me", async (req, res) => {
  const [[cliente]] = await pool.execute("SELECT * FROM cliente WHERE id = ?", [
    req.auth.clienteId,
  ]);
  const contas = await listarContas(req.auth.clienteId);

  res.json({
    cliente: formatarCliente(cliente),
    contas: contas.map(formatarConta),
  });
});

module.exports = router;
