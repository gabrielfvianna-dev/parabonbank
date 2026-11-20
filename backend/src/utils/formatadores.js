const { paraCentavos, paraNumero } = require("./dinheiro");

// Converte "AAAA-MM-DD" (MySQL) para "DD-MM-AAAA" (formato usado no app).
const dataParaApp = (dataSql) => {
  if (!dataSql) {
    return null;
  }

  const [ano, mes, dia] = dataSql.slice(0, 10).split("-");
  return `${dia}-${mes}-${ano}`;
};

// Converte "AAAA-MM-DD HH:MM:SS" (MySQL) para ISO 8601 ("AAAA-MM-DDTHH:MM:SS").
const dataHoraParaApp = (dataHoraSql) => {
  return dataHoraSql ? dataHoraSql.replace(" ", "T") : null;
};

// Converte uma linha da tabela cliente para o JSON do app.
// Os nomes seguem os campos do frontend (fullName, cpf, birthDate, email, phone).
const formatarCliente = (cliente) => ({
  id: Number(cliente.id),
  fullName: cliente.nome_completo,
  socialName: cliente.nome_social,
  cpf: cliente.cpf,
  birthDate: dataParaApp(cliente.data_nascimento),
  email: cliente.email,
  phone: cliente.telefone,
  status: cliente.status,
  createdAt: dataHoraParaApp(cliente.data_cadastro),
  lastAccessAt: dataHoraParaApp(cliente.ultimo_acesso),
});

// Converte uma linha da tabela conta (com dados da agência) para o JSON do app.
const formatarConta = (conta) => ({
  id: Number(conta.id),
  bankCode: conta.codigo_banco,
  agency: conta.codigo_agencia,
  agencyDigit: conta.digito_agencia,
  accountNumber: conta.numero_conta,
  accountDigit: conta.digito,
  accountType: conta.tipo_conta,
  balance: paraNumero(paraCentavos(conta.saldo)),
  overdraftLimit: paraNumero(paraCentavos(conta.limite_cheque_especial)),
  status: conta.status,
  holderType: conta.tipo_titular,
  openedAt: dataHoraParaApp(conta.data_abertura),
});

// Converte uma linha da tabela transacao para o JSON do app.
const formatarTransacao = (transacao) => ({
  id: Number(transacao.id),
  type: transacao.tipo,
  amount: paraNumero(paraCentavos(transacao.valor)),
  description: transacao.descricao,
  balanceBefore:
    transacao.saldo_anterior === null
      ? null
      : paraNumero(paraCentavos(transacao.saldo_anterior)),
  balanceAfter:
    transacao.saldo_posterior === null
      ? null
      : paraNumero(paraCentavos(transacao.saldo_posterior)),
  status: transacao.status,
  identifier: transacao.identificador,
  dateTime: dataHoraParaApp(transacao.data_hora),
});

// Converte uma linha da tabela chave_pix para o JSON do app.
const formatarChavePix = (chave) => ({
  id: Number(chave.id),
  accountId: Number(chave.conta_id),
  keyType: chave.tipo_chave,
  key: chave.chave,
  status: chave.status,
  createdAt: dataHoraParaApp(chave.criada_em),
});

module.exports = {
  dataParaApp,
  dataHoraParaApp,
  formatarCliente,
  formatarConta,
  formatarTransacao,
  formatarChavePix,
};
