const express = require("express");

const config = require("../config");
const { pool, transacao } = require("../db");
const { autenticar } = require("../middlewares/autenticacao");
const {
  conferirSenha,
  gerarHashSenha,
  gerarTokenSessao,
  hashToken,
} = require("../seguranca/criptografia");
const { registrarAuditoria } = require("../servicos/auditoria");
const { abrirConta, listarContas } = require("../servicos/contas");
const {
  limparTentativas,
  registrarSenhaErrada,
} = require("../servicos/tentativas");
const { ErroApi } = require("../utils/erros");
const {
  dataHoraParaApp,
  formatarCliente,
  formatarConta,
} = require("../utils/formatadores");
const {
  birthDateToSql,
  onlyNumbers,
  texto,
  validarCadastro,
} = require("../validacoes");

const router = express.Router();

// ------------------------------------------------------------
// POST /api/auth/cadastro
// Recebe exatamente os campos da tela app/cadastro.js.
// ------------------------------------------------------------
router.post("/cadastro", async (req, res) => {
  const body = req.body;
  const errors = validarCadastro(body);

  if (Object.keys(errors).length > 0) {
    throw new ErroApi(400, "Verifique os dados informados.", errors);
  }

  // Normaliza os dados para o formato das colunas do banco.
  const dados = {
    nome: texto(body.fullName).trim(),
    cpf: onlyNumbers(body.cpf),
    nascimento: birthDateToSql(body.birthDate),
    email: texto(body.email).trim().toLowerCase(),
    telefone: onlyNumbers(body.phone),
  };

  // Verifica se CPF ou e-mail já existem.
  const [existentes] = await pool.execute(
    "SELECT cpf, email FROM cliente WHERE cpf = ? OR email = ?",
    [dados.cpf, dados.email],
  );
  const duplicados = {};

  for (const cliente of existentes) {
    if (cliente.cpf === dados.cpf) {
      duplicados.cpf = "Este CPF já está cadastrado.";
    }
    if (cliente.email === dados.email) {
      duplicados.email = "Este e-mail já está cadastrado.";
    }
  }

  if (Object.keys(duplicados).length > 0) {
    throw new ErroApi(409, "Verifique os dados informados.", duplicados);
  }

  // A senha é guardada somente como hash bcrypt.
  // O PIN é validado, mas NÃO é gravado: o banco não possui coluna para ele.
  const senhaHash = await gerarHashSenha(body.password);

  let resultado;

  try {
    resultado = await transacao(async (conexao) => {
      const [cliente] = await conexao.execute(
        `INSERT INTO cliente (cpf, nome_completo, data_nascimento, email, telefone)
         VALUES (?, ?, ?, ?, ?)`,
        [dados.cpf, dados.nome, dados.nascimento, dados.email, dados.telefone],
      );
      const clienteId = cliente.insertId;

      const [usuario] = await conexao.execute(
        "INSERT INTO usuario_acesso (cliente_id, senha_hash) VALUES (?, ?)",
        [clienteId, senhaHash],
      );

      const contaId = await abrirConta(conexao);

      await conexao.execute(
        `INSERT INTO titularidade (conta_id, cliente_id, tipo_titular)
         VALUES (?, ?, 'TITULAR')`,
        [contaId, clienteId],
      );

      // O aceite dos termos fica registrado na auditoria.
      for (const acao of ["CADASTRO", "ACEITE_TERMOS"]) {
        await registrarAuditoria(
          {
            clienteId,
            usuarioId: usuario.insertId,
            acao,
            entidade: "cliente",
            entidadeId: clienteId,
            ip: req.ip,
            resultado: "SUCESSO",
          },
          conexao,
        );
      }

      const [[clienteCriado]] = await conexao.execute(
        "SELECT * FROM cliente WHERE id = ?",
        [clienteId],
      );
      const [conta] = await listarContas(clienteId, conexao);

      return { cliente: clienteCriado, conta };
    });
  } catch (erro) {
    // Dois cadastros iguais ao mesmo tempo: o UNIQUE do banco barra o segundo.
    if (erro.code === "ER_DUP_ENTRY") {
      throw new ErroApi(409, "Este CPF ou e-mail já está cadastrado.");
    }
    throw erro;
  }

  res.status(201).json({
    message: "Conta criada com sucesso.",
    cliente: formatarCliente(resultado.cliente),
    conta: formatarConta(resultado.conta),
  });
});

// ------------------------------------------------------------
// POST /api/auth/login
// Recebe os campos da tela app/login.js: identifier (e-mail ou CPF) e password.
// ------------------------------------------------------------
router.post("/login", async (req, res) => {
  const identifier = texto(req.body.identifier).trim();
  const password = texto(req.body.password);
  const errors = {};

  if (!identifier) {
    errors.identifier = "Informe seu e-mail ou CPF.";
  }

  if (!password) {
    errors.password = "Informe sua senha.";
  }

  if (Object.keys(errors).length > 0) {
    throw new ErroApi(400, "Verifique os dados informados.", errors);
  }

  // Se tiver "@" é e-mail; senão, considera os números como CPF.
  const porEmail = identifier.includes("@");
  const valorBusca = porEmail ? identifier.toLowerCase() : onlyNumbers(identifier);

  const [linhas] = await pool.execute(
    `SELECT cl.*, ua.id AS usuario_id, ua.senha_hash,
            ua.status AS usuario_status,
            ua.bloqueado_ate IS NOT NULL AND ua.bloqueado_ate > NOW() AS bloqueado
       FROM cliente cl
       JOIN usuario_acesso ua ON ua.cliente_id = cl.id
      WHERE ${porEmail ? "cl.email" : "cl.cpf"} = ?`,
    [valorBusca],
  );

  const credenciaisInvalidas = new ErroApi(401, "E-mail/CPF ou senha inválidos.");

  if (linhas.length === 0) {
    // Compara com um hash falso para o tempo de resposta ser o mesmo.
    await conferirSenha(password, null);
    throw credenciaisInvalidas;
  }

  const usuario = linhas[0];
  const auditoriaBase = {
    clienteId: usuario.id,
    usuarioId: usuario.usuario_id,
    acao: "LOGIN",
    entidade: "usuario_acesso",
    entidadeId: usuario.usuario_id,
    ip: req.ip,
  };

  if (Number(usuario.bloqueado) === 1) {
    await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });
    throw new ErroApi(
      423,
      "Acesso bloqueado temporariamente por excesso de tentativas. Tente novamente mais tarde.",
    );
  }

  const senhaCorreta = await conferirSenha(password, usuario.senha_hash);

  if (!senhaCorreta) {
    const bloqueou = await registrarSenhaErrada(usuario.usuario_id);
    await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });

    if (bloqueou) {
      throw new ErroApi(
        423,
        "Acesso bloqueado temporariamente por excesso de tentativas. Tente novamente mais tarde.",
      );
    }
    throw credenciaisInvalidas;
  }

  if (usuario.status !== "ATIVO" || usuario.usuario_status !== "ATIVO") {
    await registrarAuditoria({ ...auditoriaBase, resultado: "FALHA" });
    throw new ErroApi(403, "Acesso não permitido. Entre em contato com o banco.");
  }

  // Senha correta: cria a sessão. O token vai para o app;
  // no banco fica apenas o hash SHA-256 dele.
  const token = gerarTokenSessao();

  const sessao = await transacao(async (conexao) => {
    await limparTentativas(usuario.usuario_id, conexao);
    await conexao.execute(
      "UPDATE usuario_acesso SET ultimo_login = NOW() WHERE id = ?",
      [usuario.usuario_id],
    );
    await conexao.execute(
      "UPDATE cliente SET ultimo_acesso = NOW() WHERE id = ?",
      [usuario.id],
    );

    const [nova] = await conexao.execute(
      `INSERT INTO sessao (cliente_id, token_hash, expiracao)
       VALUES (?, ?, DATE_ADD(NOW(), INTERVAL ? MINUTE))`,
      [usuario.id, hashToken(token), config.sessaoMinutos],
    );

    await registrarAuditoria(
      { ...auditoriaBase, resultado: "SUCESSO" },
      conexao,
    );

    const [[criada]] = await conexao.execute(
      "SELECT expiracao FROM sessao WHERE id = ?",
      [nova.insertId],
    );
    const [[clienteAtual]] = await conexao.execute(
      "SELECT * FROM cliente WHERE id = ?",
      [usuario.id],
    );

    return { expiracao: criada.expiracao, cliente: clienteAtual };
  });

  res.json({
    message: "Login realizado com sucesso.",
    token,
    tokenType: "Bearer",
    expiresAt: dataHoraParaApp(sessao.expiracao),
    cliente: formatarCliente(sessao.cliente),
  });
});

// ------------------------------------------------------------
// POST /api/auth/logout  (precisa estar logado)
// ------------------------------------------------------------
router.post("/logout", autenticar, async (req, res) => {
  await pool.execute(
    `UPDATE sessao SET status = 'ENCERRADA', encerrado_em = NOW()
      WHERE id = ?`,
    [req.auth.sessaoId],
  );

  await registrarAuditoria({
    clienteId: req.auth.clienteId,
    usuarioId: req.auth.usuarioId,
    acao: "LOGOUT",
    entidade: "sessao",
    entidadeId: req.auth.sessaoId,
    ip: req.ip,
    resultado: "SUCESSO",
  });

  res.json({ message: "Sessão encerrada." });
});

module.exports = router;
