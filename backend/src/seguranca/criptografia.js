const crypto = require("node:crypto");
const bcrypt = require("bcryptjs");

const config = require("../config");

// Hash usado quando o usuário não existe, para que o tempo de resposta
// do login seja parecido e não revele se o e-mail/CPF está cadastrado.
const HASH_FALSO = bcrypt.hashSync("parabon-hash-falso", 10);

// Gera o hash bcrypt da senha (gravado em usuario_acesso.senha_hash).
const gerarHashSenha = (senha) => {
  return bcrypt.hash(senha, config.bcryptCusto);
};

// Compara a senha digitada com o hash gravado no banco.
// Hashes inválidos (como os de exemplo do script SQL) retornam false.
const conferirSenha = async (senha, hash) => {
  try {
    return await bcrypt.compare(senha, hash || HASH_FALSO);
  } catch {
    return false;
  }
};

// Gera o token de sessão entregue ao aplicativo.
// 32 bytes aleatórios = 256 bits, em base64url (seguro para URL e header).
const gerarTokenSessao = () => {
  return crypto.randomBytes(32).toString("base64url");
};

// O banco guarda somente o SHA-256 do token (sessao.token_hash),
// nunca o token em si. Se o banco vazar, os tokens não podem ser usados.
const hashToken = (token) => {
  return crypto.createHash("sha256").update(token).digest("hex");
};

// Identificador único para transacao.identificador e chaves aleatórias.
const gerarUuid = () => crypto.randomUUID();

// Identificador do Pix no padrão E + ISPB(8) + AAAAMMDDHHmm + 11 caracteres.
const gerarEndToEndId = () => {
  const ispb = String(config.bancoCodigo).padStart(8, "0").slice(-8);
  const agora = new Date();
  const data = [
    agora.getUTCFullYear(),
    String(agora.getUTCMonth() + 1).padStart(2, "0"),
    String(agora.getUTCDate()).padStart(2, "0"),
    String(agora.getUTCHours()).padStart(2, "0"),
    String(agora.getUTCMinutes()).padStart(2, "0"),
  ].join("");
  const alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const bytes = crypto.randomBytes(11);
  const sufixo = Array.from(bytes, (b) => alfabeto[b % alfabeto.length]).join(
    "",
  );

  return `E${ispb}${data}${sufixo}`;
};

module.exports = {
  gerarHashSenha,
  conferirSenha,
  gerarTokenSessao,
  hashToken,
  gerarUuid,
  gerarEndToEndId,
};
