const express = require("express");

const { transacao } = require("../db");
const { autenticar } = require("../middlewares/autenticacao");
const { gerarUuid } = require("../seguranca/criptografia");
const { buscarContaDoCliente } = require("../servicos/contas");
const { lerValor, paraCentavos, paraDecimal } = require("../utils/dinheiro");
const { ErroApi } = require("../utils/erros");
const { formatarConta } = require("../utils/formatadores");

// ROTAS SOMENTE PARA DESENVOLVIMENTO E TESTES.
// Só existem quando HABILITAR_ROTAS_DEV=true no .env.
const router = express.Router();

router.use(autenticar);

// POST /api/dev/contas/:id/deposito — coloca saldo na conta para testar o Pix.
// Body: { "amount": 1000 }
router.post("/contas/:id/deposito", async (req, res) => {
  const centavos = lerValor(req.body.amount);

  if (centavos === null || centavos <= 0) {
    throw new ErroApi(400, "Verifique os dados informados.", {
      amount: "Informe um valor válido.",
    });
  }

  const conta = await buscarContaDoCliente(req.params.id, req.auth.clienteId);

  await transacao(async (conexao) => {
    const [[travada]] = await conexao.execute(
      "SELECT saldo FROM conta WHERE id = ? FOR UPDATE",
      [conta.id],
    );
    const saldoAnterior = paraCentavos(travada.saldo);
    const saldoPosterior = saldoAnterior + centavos;

    await conexao.execute(
      `INSERT INTO transacao
         (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
       VALUES (?, 'DEPOSITO', ?, 'Depósito de teste', ?, ?, ?)`,
      [
        conta.id,
        paraDecimal(centavos),
        paraDecimal(saldoAnterior),
        paraDecimal(saldoPosterior),
        gerarUuid(),
      ],
    );
    await conexao.execute("UPDATE conta SET saldo = ? WHERE id = ?", [
      paraDecimal(saldoPosterior),
      conta.id,
    ]);
  });

  const atualizada = await buscarContaDoCliente(conta.id, req.auth.clienteId);

  res.status(201).json({
    message: "Depósito de teste realizado.",
    conta: formatarConta(atualizada),
  });
});

module.exports = router;
