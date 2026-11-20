const cors = require("cors");
const express = require("express");
const rateLimit = require("express-rate-limit");
const helmet = require("helmet");

const config = require("./config");
const { pool } = require("./db");
const { rotaNaoEncontrada, tratarErros } = require("./middlewares/erros");

const app = express();

// Cabeçalhos de segurança HTTP.
app.use(helmet());
app.disable("x-powered-by");

// Permite que o Expo web (navegador) chame a API.
// O app no celular (Expo Go) não depende de CORS.
app.use(
  cors({
    origin: config.corsOrigins.includes("*") ? true : config.corsOrigins,
  }),
);

// Lê o corpo das requisições em JSON (limite de 10 KB).
app.use(express.json({ limit: "10kb" }));
app.use((req, res, next) => {
  if (req.body === undefined || req.body === null) {
    req.body = {};
  }
  next();
});

// Limita tentativas de login/cadastro por IP (proteção contra força bruta).
const limiteAuth = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: config.rateLimitAuthMax,
  standardHeaders: "draft-8",
  legacyHeaders: false,
  message: { message: "Muitas tentativas. Aguarde alguns minutos." },
});

// Limita envios de Pix por IP.
const limitePix = rateLimit({
  windowMs: 60 * 1000,
  limit: config.rateLimitPixMax,
  standardHeaders: "draft-8",
  legacyHeaders: false,
  message: { message: "Muitas operações seguidas. Aguarde um minuto." },
});

// Verifica se a API e o banco estão funcionando.
app.get("/api/health", async (req, res) => {
  try {
    await pool.query("SELECT 1");
    res.json({ status: "ok", database: "ok" });
  } catch {
    res.status(503).json({ status: "erro", database: "indisponível" });
  }
});

app.use("/api/auth/login", limiteAuth);
app.use("/api/auth/cadastro", limiteAuth);
app.use("/api/pix/enviar", limitePix);

app.use("/api/auth", require("./rotas/auth"));
app.use("/api/clientes", require("./rotas/clientes"));
app.use("/api/contas", require("./rotas/contas"));
app.use("/api/pix", require("./rotas/pix"));

if (config.habilitarRotasDev) {
  app.use("/api/dev", require("./rotas/dev"));
}

app.use(rotaNaoEncontrada);
app.use(tratarErros);

module.exports = app;
