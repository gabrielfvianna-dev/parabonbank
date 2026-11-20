const crypto = require("node:crypto");

const config = require("../config");
const { pool } = require("../db");
const { ErroApi } = require("../utils/erros");

// Consulta base das contas de um cliente (somente titularidades vigentes).
const SELECT_CONTAS = `
  SELECT c.*, a.codigo_agencia, a.digito AS digito_agencia,
         b.codigo_banco, t.tipo_titular
    FROM conta c
    JOIN agencia a ON a.id = c.agencia_id
    JOIN banco b ON b.id = a.banco_id
    JOIN titularidade t ON t.conta_id = c.id
   WHERE t.cliente_id = ? AND t.data_fim IS NULL`;

// Lista as contas do cliente. A conta em que ele é TITULAR vem primeiro.
const listarContas = async (clienteId, executor = pool) => {
  const [contas] = await executor.execute(
    `${SELECT_CONTAS}
     ORDER BY t.tipo_titular = 'TITULAR' DESC, c.id`,
    [clienteId],
  );

  return contas;
};

// Busca uma conta garantindo que ela pertence ao cliente.
// Responde 404 (e não 403) para não revelar contas de outras pessoas.
const buscarContaDoCliente = async (contaId, clienteId, executor = pool) => {
  const id = Number(contaId);

  if (!Number.isInteger(id) || id <= 0) {
    throw new ErroApi(404, "Conta não encontrada.");
  }

  const [contas] = await executor.execute(`${SELECT_CONTAS} AND c.id = ?`, [
    clienteId,
    id,
  ]);

  if (contas.length === 0) {
    throw new ErroApi(404, "Conta não encontrada.");
  }

  return contas[0];
};

// Retorna a conta informada ou, se nenhuma foi informada, a conta principal.
const resolverContaOrigem = async (contaId, clienteId, executor = pool) => {
  if (contaId !== undefined && contaId !== null && contaId !== "") {
    return buscarContaDoCliente(contaId, clienteId, executor);
  }

  const contas = await listarContas(clienteId, executor);

  if (contas.length === 0) {
    throw new ErroApi(404, "Nenhuma conta encontrada para este cliente.");
  }

  return contas[0];
};

// Busca a agência configurada (BANCO_CODIGO + AGENCIA_CODIGO no .env).
const buscarAgenciaPadrao = async (executor = pool) => {
  const [agencias] = await executor.execute(
    `SELECT a.id
       FROM agencia a
       JOIN banco b ON b.id = a.banco_id
      WHERE b.codigo_banco = ? AND a.codigo_agencia = ?
        AND a.status = 'ATIVA' AND b.status = 'ATIVO'`,
    [config.bancoCodigo, config.agenciaCodigo],
  );

  if (agencias.length === 0) {
    throw new Error(
      `Agência ${config.agenciaCodigo} do banco ${config.bancoCodigo} não encontrada. ` +
        "Confira BANCO_CODIGO e AGENCIA_CODIGO no .env.",
    );
  }

  return agencias[0].id;
};

// Dígito verificador da conta (módulo 11).
const calcularDigito = (numero) => {
  let soma = 0;
  let peso = 2;

  for (let i = numero.length - 1; i >= 0; i--) {
    soma += Number(numero[i]) * peso;
    peso = peso === 9 ? 2 : peso + 1;
  }

  const resto = 11 - (soma % 11);
  return resto >= 10 ? "0" : String(resto);
};

// Abre uma conta DIGITAL na agência padrão, com número aleatório de 8 dígitos.
const abrirConta = async (executor) => {
  const agenciaId = await buscarAgenciaPadrao(executor);

  for (let tentativa = 0; tentativa < 10; tentativa++) {
    const numero = String(crypto.randomInt(10000000, 100000000));
    const [existe] = await executor.execute(
      "SELECT id FROM conta WHERE agencia_id = ? AND numero_conta = ?",
      [agenciaId, numero],
    );

    if (existe.length > 0) {
      continue;
    }

    const [resultado] = await executor.execute(
      `INSERT INTO conta (agencia_id, numero_conta, digito, tipo_conta)
       VALUES (?, ?, ?, 'DIGITAL')`,
      [agenciaId, numero, calcularDigito(numero)],
    );

    return resultado.insertId;
  }

  throw new Error("Não foi possível gerar um número de conta livre.");
};

module.exports = {
  listarContas,
  buscarContaDoCliente,
  resolverContaOrigem,
  abrirConta,
  calcularDigito,
};
