const fs = require("node:fs");
const path = require("node:path");

// Carrega o arquivo .env da pasta backend, se ele existir.
const envPath = path.join(__dirname, "..", ".env");

if (fs.existsSync(envPath)) {
  process.loadEnvFile(envPath);
}

// Lê um número das variáveis de ambiente, usando um valor padrão.
const numero = (nome, padrao) => {
  const valor = Number(process.env[nome]);
  return Number.isFinite(valor) && process.env[nome] !== "" ? valor : padrao;
};

const config = {
  port: numero("PORT", 3000),

  db: {
    host: process.env.DB_HOST || "localhost",
    port: numero("DB_PORT", 3306),
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD || "",
    database: process.env.DB_NAME || "sistema_bancario",
  },

  bancoCodigo: process.env.BANCO_CODIGO || "999",
  agenciaCodigo: process.env.AGENCIA_CODIGO || "0001",

  bcryptCusto: numero("BCRYPT_CUSTO", 12),
  sessaoMinutos: numero("SESSAO_MINUTOS", 480),
  loginMaxTentativas: numero("LOGIN_MAX_TENTATIVAS", 5),
  loginBloqueioMinutos: numero("LOGIN_BLOQUEIO_MINUTOS", 15),
  rateLimitAuthMax: numero("RATE_LIMIT_AUTH_MAX", 20),
  rateLimitPixMax: numero("RATE_LIMIT_PIX_MAX", 30),
  pixLimitePorTransacao: numero("PIX_LIMITE_POR_TRANSACAO", 10000),

  corsOrigins: (
    process.env.CORS_ORIGINS || "http://localhost:8081,http://localhost:19006"
  )
    .split(",")
    .map((origem) => origem.trim())
    .filter(Boolean),

  habilitarRotasDev: process.env.HABILITAR_ROTAS_DEV === "true",
};

module.exports = config;
