const express = require("express");

const config = require("../config");
const { pool, transacao } = require("../db");
const { autenticar } = require("../middlewares/autenticacao");
const {
  conferirSenha,
  gerarEndToEndId,
  gerarUuid,
} = require("../seguranca/criptografia");
const { registrarAuditoria } = require("../servicos/auditoria");
const {
  buscarContaDoCliente,
  resolverContaOrigem,
} = require("../servicos/contas");
const {
  limparTentativas,
  registrarSenhaErrada,
} = require("../servicos/tentativas");
const {
  lerValor,
  paraCentavos,
  paraDecimal,
  paraNumero,
} = require("../utils/dinheiro");
const { ErroApi } = require("../utils/erros");
const {
  dataHoraParaApp,
  formatarChavePix,
  formatarConta,
} = require("../utils/formatadores");
const { onlyNumbers, texto } = require("../validacoes");

const router = express.Router();

router.use(autenticar);

const TIPOS_CHAVE = ["CPF", "EMAIL", "TELEFONE", "ALEATORIA"];
const MAX_CHAVES_ALEATORIAS = 5;
const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Formas possíveis de uma chave digitada pelo usuário, na ordem de busca.
// Ex.: "12999990001" pode ser um CPF ou um telefone (+5512999990001).
const formasDaChave = (chave) => {
  if (chave.includes("@")) {
    return [chave.toLowerCase()];
  }

  if (UUID_REGEX.test(chave)) {
    return [chave.toLowerCase()];
  }

  const numeros = onlyNumbers(chave);

  if (chave.startsWith("+")) {
    return [`+${numeros}`];
  }

  if (numeros.length === 11) {
    return [numeros, `+55${numeros}`];
  }

  if (numeros.length === 10) {
    return [`+55${numeros}`];
  }

  if (numeros.length >= 12 && numeros.startsWith("55")) {
    return [`+${numeros}`];
  }

  return [chave];
};

// ------------------------------------------------------------
// GET /api/pix/chaves — chaves Pix ativas do cliente logado.
// ------------------------------------------------------------
router.get("/chaves", async (req, res) => {
  const [chaves] = await pool.execute(
    `SELECT * FROM chave_pix
      WHERE cliente_id = ? AND status = 'ATIVA'
      ORDER BY id`,
    [req.auth.clienteId],
  );

  res.json({ chaves: chaves.map(formatarChavePix) });
});

// ------------------------------------------------------------
// POST /api/pix/chaves — cadastra uma chave Pix.
// Body: { "keyType": "CPF" | "EMAIL" | "TELEFONE" | "ALEATORIA", "accountId"?: 1 }
// O valor da chave vem do cadastro do cliente (não é digitado).
// ------------------------------------------------------------
router.post("/chaves", async (req, res) => {
  const tipo = texto(req.body.keyType).trim().toUpperCase();

  if (!TIPOS_CHAVE.includes(tipo)) {
    throw new ErroApi(400, "Verifique os dados informados.", {
      keyType: "Tipo de chave inválido. Use CPF, EMAIL, TELEFONE ou ALEATORIA.",
    });
  }

  const clienteId = req.auth.clienteId;
  const conta = await resolverContaOrigem(req.body.accountId, clienteId);

  if (conta.status !== "ATIVA") {
    throw new ErroApi(422, "Esta conta não pode receber chaves Pix.");
  }

  const [[cliente]] = await pool.execute("SELECT * FROM cliente WHERE id = ?", [
    clienteId,
  ]);

  let valor;

  if (tipo === "CPF") {
    valor = cliente.cpf;
  } else if (tipo === "EMAIL") {
    valor = cliente.email;
  } else if (tipo === "TELEFONE") {
    if (!cliente.telefone) {
      throw new ErroApi(400, "Verifique os dados informados.", {
        keyType: "Cadastre um telefone antes de criar esta chave.",
      });
    }
    valor = `+55${cliente.telefone}`;
  } else {
    const [[{ total }]] = await pool.execute(
      `SELECT COUNT(*) AS total FROM chave_pix
        WHERE cliente_id = ? AND tipo_chave = 'ALEATORIA' AND status = 'ATIVA'`,
      [clienteId],
    );

    if (Number(total) >= MAX_CHAVES_ALEATORIAS) {
      throw new ErroApi(422, "Verifique os dados informados.", {
        keyType: `Limite de ${MAX_CHAVES_ALEATORIAS} chaves aleatórias atingido.`,
      });
    }
    valor = gerarUuid();
  }

  const [existentes] = await pool.execute(
    "SELECT * FROM chave_pix WHERE chave = ?",
    [valor],
  );
  let chaveId;

  if (existentes.length > 0) {
    const existente = existentes[0];
    const ehMinhaInativa =
      Number(existente.cliente_id) === clienteId &&
      existente.status === "INATIVA";

    if (!ehMinhaInativa) {
      throw new ErroApi(409, "Verifique os dados informados.", {
        keyType: "Esta chave Pix já está cadastrada.",
      });
    }

    // A chave foi excluída antes pelo próprio cliente: reativa.
    await pool.execute(
      "UPDATE chave_pix SET status = 'ATIVA', conta_id = ? WHERE id = ?",
      [conta.id, existente.id],
    );
    chaveId = existente.id;
  } else {
    try {
      const [nova] = await pool.execute(
        `INSERT INTO chave_pix (cliente_id, conta_id, tipo_chave, chave)
         VALUES (?, ?, ?, ?)`,
        [clienteId, conta.id, tipo, valor],
      );
      chaveId = nova.insertId;
    } catch (erro) {
      if (erro.code === "ER_DUP_ENTRY") {
        throw new ErroApi(409, "Verifique os dados informados.", {
          keyType: "Esta chave Pix já está cadastrada.",
        });
      }
      throw erro;
    }
  }

  await registrarAuditoria({
    clienteId,
    usuarioId: req.auth.usuarioId,
    acao: "CADASTRO_CHAVE_PIX",
    entidade: "chave_pix",
    entidadeId: chaveId,
    ip: req.ip,
    resultado: "SUCESSO",
  });

  const [[chave]] = await pool.execute("SELECT * FROM chave_pix WHERE id = ?", [
    chaveId,
  ]);

  res.status(201).json({
    message: "Chave Pix cadastrada com sucesso.",
    chave: formatarChavePix(chave),
  });
});

// ------------------------------------------------------------
// DELETE /api/pix/chaves/:id — desativa uma chave Pix do cliente.
// ------------------------------------------------------------
router.delete("/chaves/:id", async (req, res) => {
  const [resultado] = await pool.execute(
    `UPDATE chave_pix SET status = 'INATIVA'
      WHERE id = ? AND cliente_id = ? AND status = 'ATIVA'`,
    [Number(req.params.id) || 0, req.auth.clienteId],
  );

  if (resultado.affectedRows === 0) {
    throw new ErroApi(404, "Chave Pix não encontrada.");
  }

  await registrarAuditoria({
    clienteId: req.auth.clienteId,
    usuarioId: req.auth.usuarioId,
    acao: "EXCLUSAO_CHAVE_PIX",
    entidade: "chave_pix",
    entidadeId: Number(req.params.id),
    ip: req.ip,
    resultado: "SUCESSO",
  });

  res.json({ message: "Chave Pix excluída." });
});

// ------------------------------------------------------------
// POST /api/pix/enviar — envia um Pix (API de "send").
// Body: {
//   "key": "chave do destinatário (CPF, e-mail, telefone ou aleatória)",
//   "amount": 50.25,
//   "description": "opcional, até 140 caracteres",
//   "password": "senha do usuário, para confirmar a operação",
//   "accountId": 1   (opcional; padrão = conta principal)
// }
// ------------------------------------------------------------
router.post("/enviar", async (req, res) => {
  const body = req.body;
  const clienteId = req.auth.clienteId;
  const usuarioId = req.auth.usuarioId;
  const errors = {};

  const chaveDigitada = texto(body.key).trim();
  const centavos = lerValor(body.amount);
  const limiteCentavos = Math.round(config.pixLimitePorTransacao * 100);
  const descricaoValida =
    body.description === undefined ||
    body.description === null ||
    typeof body.description === "string";
  const descricao = texto(body.description).trim();

  if (!chaveDigitada || chaveDigitada.length > 255) {
    errors.key = "Informe a chave Pix.";
  }

  if (centavos === null || centavos <= 0) {
    errors.amount = "Informe um valor válido.";
  } else if (centavos > limiteCentavos) {
    errors.amount = `O valor máximo por Pix é R$ ${paraDecimal(limiteCentavos).replace(".", ",")}.`;
  }

  if (!descricaoValida || descricao.length > 140) {
    errors.description = "A descrição deve ter no máximo 140 caracteres.";
  }

  if (!texto(body.password)) {
    errors.password = "Informe sua senha.";
  }

  if (Object.keys(errors).length > 0) {
    throw new ErroApi(400, "Verifique os dados informados.", errors);
  }

  const auditoriaBase = {
    clienteId,
    usuarioId,
    acao: "PIX_ENVIADO",
    entidade: "pix",
    ip: req.ip,
  };

  // 1) Confirma a senha (mesmo contador de tentativas do login).
  const [[usuario]] = await pool.execute(
    `SELECT senha_hash,
            bloqueado_ate IS NOT NULL AND bloqueado_ate > NOW() AS bloqueado
       FROM usuario_acesso WHERE id = ?`,
    [usuarioId],
  );

  if (Number(usuario.bloqueado) === 1) {
    throw new ErroApi(
      423,
      "Acesso bloqueado temporariamente por excesso de tentativas. Tente novamente mais tarde.",
    );
  }

  if (!(await conferirSenha(body.password, usuario.senha_hash))) {
    const bloqueou = await registrarSenhaErrada(usuarioId);
    await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });

    if (bloqueou) {
      throw new ErroApi(
        423,
        "Acesso bloqueado temporariamente por excesso de tentativas. Tente novamente mais tarde.",
      );
    }
    throw new ErroApi(401, "Senha incorreta.", { password: "Senha incorreta." });
  }

  await limparTentativas(usuarioId);

  // 2) Encontra a conta de destino pela chave Pix.
  const formas = formasDaChave(chaveDigitada);
  const [encontradas] = await pool.execute(
    `SELECT cp.chave, cp.conta_id, cl.nome_completo,
            c.numero_conta, c.digito, a.codigo_agencia, b.codigo_banco
       FROM chave_pix cp
       JOIN cliente cl ON cl.id = cp.cliente_id
       JOIN conta c ON c.id = cp.conta_id
       JOIN agencia a ON a.id = c.agencia_id
       JOIN banco b ON b.id = a.banco_id
      WHERE cp.status = 'ATIVA' AND cp.chave IN (${formas.map(() => "?").join(", ")})`,
    formas,
  );
  const destino = formas
    .map((forma) => encontradas.find((linha) => linha.chave === forma))
    .find(Boolean);

  if (!destino) {
    await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });
    throw new ErroApi(404, "Chave Pix não encontrada.", {
      key: "Chave Pix não encontrada.",
    });
  }

  // 3) Conta de origem (precisa pertencer ao cliente logado).
  const origem = await resolverContaOrigem(body.accountId, clienteId);
  const destinoId = Number(destino.conta_id);
  const origemId = Number(origem.id);

  if (origemId === destinoId) {
    throw new ErroApi(400, "Verifique os dados informados.", {
      key: "Não é possível enviar um Pix para a mesma conta.",
    });
  }

  const [[remetente]] = await pool.execute(
    "SELECT nome_completo FROM cliente WHERE id = ?",
    [clienteId],
  );

  // 4) Movimenta o dinheiro numa única transação do banco.
  //    As duas contas são travadas (FOR UPDATE) sempre na mesma ordem (por id)
  //    para evitar saldo duplicado e deadlock com Pix simultâneos.
  let pix;

  try {
    pix = await transacao(async (conexao) => {
      const ids = [origemId, destinoId].sort((a, b) => a - b);
      const [travadas] = await conexao.execute(
        `SELECT id, saldo, limite_cheque_especial, status
           FROM conta WHERE id IN (?, ?) ORDER BY id FOR UPDATE`,
        ids,
      );
      const contaOrigem = travadas.find((c) => Number(c.id) === origemId);
      const contaDestino = travadas.find((c) => Number(c.id) === destinoId);

      if (contaOrigem.status !== "ATIVA") {
        throw new ErroApi(422, "A conta de origem está bloqueada ou encerrada.");
      }

      if (contaDestino.status !== "ATIVA") {
        throw new ErroApi(422, "Verifique os dados informados.", {
          key: "A conta de destino não pode receber Pix.",
        });
      }

      const saldoOrigem = paraCentavos(contaOrigem.saldo);
      const limiteOrigem = paraCentavos(contaOrigem.limite_cheque_especial);
      const novoSaldoOrigem = saldoOrigem - centavos;

      if (novoSaldoOrigem < -limiteOrigem) {
        throw new ErroApi(422, "Saldo insuficiente.", {
          amount: "Saldo insuficiente.",
        });
      }

      const saldoDestino = paraCentavos(contaDestino.saldo);
      const novoSaldoDestino = saldoDestino + centavos;
      const valor = paraDecimal(centavos);
      const endToEndId = gerarEndToEndId();

      const [novoPix] = await conexao.execute(
        `INSERT INTO pix
           (conta_origem_id, conta_destino_id, chave_destino, valor, descricao, end_to_end_id)
         VALUES (?, ?, ?, ?, ?, ?)`,
        [origemId, destinoId, destino.chave, valor, descricao || null, endToEndId],
      );

      const [saida] = await conexao.execute(
        `INSERT INTO transacao
           (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
         VALUES (?, 'PIX_ENVIADO', ?, ?, ?, ?, ?)`,
        [
          origemId,
          valor,
          (descricao || `Pix enviado para ${destino.nome_completo}`).slice(0, 255),
          paraDecimal(saldoOrigem),
          paraDecimal(novoSaldoOrigem),
          gerarUuid(),
        ],
      );

      await conexao.execute("UPDATE conta SET saldo = ? WHERE id = ?", [
        paraDecimal(novoSaldoOrigem),
        origemId,
      ]);

      const [entrada] = await conexao.execute(
        `INSERT INTO transacao
           (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
         VALUES (?, 'PIX_RECEBIDO', ?, ?, ?, ?, ?)`,
        [
          destinoId,
          valor,
          (descricao || `Pix recebido de ${remetente.nome_completo}`).slice(0, 255),
          paraDecimal(saldoDestino),
          paraDecimal(novoSaldoDestino),
          gerarUuid(),
        ],
      );

      await conexao.execute("UPDATE conta SET saldo = ? WHERE id = ?", [
        paraDecimal(novoSaldoDestino),
        destinoId,
      ]);

      await conexao.execute(
        `UPDATE pix
            SET status = 'CONCLUIDO', transacao_origem_id = ?, transacao_destino_id = ?
          WHERE id = ?`,
        [saida.insertId, entrada.insertId, novoPix.insertId],
      );

      await registrarAuditoria(
        { ...auditoriaBase, entidadeId: novoPix.insertId, resultado: "SUCESSO" },
        conexao,
      );

      const [[criado]] = await conexao.execute("SELECT * FROM pix WHERE id = ?", [
        novoPix.insertId,
      ]);

      return criado;
    });
  } catch (erro) {
    if (erro instanceof ErroApi) {
      await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });
    }
    throw erro;
  }

  const contaAtualizada = await buscarContaDoCliente(origemId, clienteId);

  res.status(201).json({
    message: "Pix enviado com sucesso.",
    pix: {
      id: Number(pix.id),
      endToEndId: pix.end_to_end_id,
      amount: paraNumero(paraCentavos(pix.valor)),
      description: pix.descricao,
      status: pix.status,
      dateTime: dataHoraParaApp(pix.data_hora),
      recipient: {
        name: destino.nome_completo,
        bankCode: destino.codigo_banco,
        agency: destino.codigo_agencia,
        accountNumber: destino.numero_conta,
        accountDigit: destino.digito,
      },
    },
    conta: formatarConta(contaAtualizada),
  });
});

module.exports = router;
