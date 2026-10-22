const mysql = require("mysql2/promise");

const config = require("./config");

// Pool de conexões com o MySQL.
// dateStrings: as datas chegam como texto ("2026-10-19 15:07:00"),
// evitando conversões de fuso horário.
// decimalNumbers fica desligado: valores DECIMAL chegam como texto
// e são convertidos para centavos em utils/dinheiro.js, sem perder precisão.
const pool = mysql.createPool({
  ...config.db,
  charset: "utf8mb4",
  dateStrings: true,
  waitForConnections: true,
  connectionLimit: 10,
});

// Executa uma função dentro de uma transação.
// Se a função lançar erro, tudo é desfeito (ROLLBACK).
const transacao = async (fn) => {
  const conexao = await pool.getConnection();

  try {
    await conexao.beginTransaction();
    const resultado = await fn(conexao);
    await conexao.commit();
    return resultado;
  } catch (erro) {
    await conexao.rollback();
    throw erro;
  } finally {
    conexao.release();
  }
};

module.exports = { pool, transacao };
