// Validações do backend.
// As regras e as mensagens são as MESMAS do frontend (app/cadastro.js),
// e os erros usam os MESMOS nomes de campo (fullName, cpf, birthDate...),
// para que o app possa fazer setErrors(resposta.errors) diretamente.

const MENSAGENS = {
  fullName: "Informe seu nome completo.",
  cpf: "Informe um CPF válido.",
  birthDate: "Informe uma data válida e tenha pelo menos 18 anos.",
  email: "Informe um e-mail válido.",
  phone: "Informe um telefone válido.",
  password:
    "A senha deve ter 8–64 caracteres, com maiúscula, minúscula, número e caractere especial.",
  confirmPassword: "As senhas não são iguais.",
  pin: "O PIN deve ter 6 dígitos e não pode ser uma sequência ou repetição.",
  confirmPin: "Os PINs não são iguais.",
  terms: "Aceite os termos para continuar.",
};

// Garante que o valor recebido seja texto (o JSON pode trazer qualquer tipo).
const texto = (valor) => (typeof valor === "string" ? valor : "");

// Remove caracteres que não sejam números.
const onlyNumbers = (value) => texto(value).replace(/\D/g, "");

// Valida o CPF utilizando os dois dígitos verificadores.
const validateCPF = (value) => {
  const numbers = onlyNumbers(value);

  if (numbers.length !== 11) {
    return false;
  }

  if (/^(\d)\1{10}$/.test(numbers)) {
    return false;
  }

  let sum = 0;

  for (let i = 0; i < 9; i++) {
    sum += Number(numbers[i]) * (10 - i);
  }

  let remainder = (sum * 10) % 11;

  if (remainder === 10) {
    remainder = 0;
  }

  if (remainder !== Number(numbers[9])) {
    return false;
  }

  sum = 0;

  for (let i = 0; i < 10; i++) {
    sum += Number(numbers[i]) * (11 - i);
  }

  remainder = (sum * 10) % 11;

  if (remainder === 10) {
    remainder = 0;
  }

  return remainder === Number(numbers[10]);
};

// Valida o formato básico do e-mail.
const validateEmail = (value) => {
  const email = texto(value);
  return email.length <= 150 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

// Converte "DD-MM-AAAA" (formato do app) para "AAAA-MM-DD" (formato do MySQL).
// Retorna null se a data não existir.
const birthDateToSql = (value) => {
  const data = texto(value);

  if (!/^\d{2}-\d{2}-\d{4}$/.test(data)) {
    return null;
  }

  const [day, month, year] = data.split("-").map(Number);
  const date = new Date(year, month - 1, day);

  if (
    date.getFullYear() !== year ||
    date.getMonth() + 1 !== month ||
    date.getDate() !== day
  ) {
    return null;
  }

  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
};

// Valida a data e verifica a idade mínima de 18 anos.
const validateBirthDate = (value) => {
  const sql = birthDateToSql(value);

  if (!sql) {
    return false;
  }

  const [year, month, day] = sql.split("-").map(Number);
  const today = new Date();
  let age = today.getFullYear() - year;

  const hasBirthdayPassed =
    today.getMonth() + 1 > month ||
    (today.getMonth() + 1 === month && today.getDate() >= day);

  if (!hasBirthdayPassed) {
    age--;
  }

  return age >= 18 && year >= 1900;
};

// Valida telefone brasileiro com 10 ou 11 dígitos.
const validatePhone = (value) => {
  const numbers = onlyNumbers(value);
  return numbers.length === 10 || numbers.length === 11;
};

// Valida as regras definidas para a senha.
const validatePassword = (value) => {
  const senha = texto(value);

  if (senha.length < 8 || senha.length > 64) {
    return false;
  }

  return (
    /[A-Z]/.test(senha) &&
    /[a-z]/.test(senha) &&
    /\d/.test(senha) &&
    /[^A-Za-z0-9]/.test(senha)
  );
};

// Valida as regras básicas do PIN.
const validatePin = (value) => {
  const pin = texto(value);

  if (!/^\d{6}$/.test(pin)) {
    return false;
  }

  if (/^(\d)\1{5}$/.test(pin)) {
    return false;
  }

  return pin !== "123456" && pin !== "654321";
};

// Valida todos os campos da tela de cadastro.
// Retorna um objeto { campo: mensagem } — vazio quando está tudo certo.
const validarCadastro = (body) => {
  const errors = {};
  const fullName = texto(body.fullName).trim();

  if (fullName.length < 3 || fullName.length > 150) {
    errors.fullName = MENSAGENS.fullName;
  }

  if (!validateCPF(body.cpf)) {
    errors.cpf = MENSAGENS.cpf;
  }

  if (!validateBirthDate(body.birthDate)) {
    errors.birthDate = MENSAGENS.birthDate;
  }

  if (!validateEmail(texto(body.email).trim())) {
    errors.email = MENSAGENS.email;
  }

  if (!validatePhone(body.phone)) {
    errors.phone = MENSAGENS.phone;
  }

  if (!validatePassword(body.password)) {
    errors.password = MENSAGENS.password;
  }

  if (texto(body.password) !== texto(body.confirmPassword)) {
    errors.confirmPassword = MENSAGENS.confirmPassword;
  }

  if (!validatePin(body.pin)) {
    errors.pin = MENSAGENS.pin;
  }

  if (texto(body.pin) !== texto(body.confirmPin)) {
    errors.confirmPin = MENSAGENS.confirmPin;
  }

  if (body.termsAccepted !== true) {
    errors.terms = MENSAGENS.terms;
  }

  return errors;
};

module.exports = {
  MENSAGENS,
  texto,
  onlyNumbers,
  validateCPF,
  validateEmail,
  validateBirthDate,
  birthDateToSql,
  validatePhone,
  validatePassword,
  validatePin,
  validarCadastro,
};
