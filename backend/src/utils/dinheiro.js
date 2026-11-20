// Os cálculos de dinheiro são feitos em CENTAVOS (números inteiros)
// para evitar erros de arredondamento (ex.: 0.1 + 0.2 = 0.30000000000000004).

// Converte o DECIMAL do MySQL ("2500.00" ou "-10.5") para centavos.
const paraCentavos = (decimal) => {
  const [inteiro, fracao = ""] = String(decimal).replace("-", "").split(".");
  const centavos = Number(inteiro) * 100 + Number(fracao.padEnd(2, "0").slice(0, 2));
  return String(decimal).startsWith("-") ? -centavos : centavos;
};

// Converte centavos para o texto aceito pelo MySQL ("2500.00").
const paraDecimal = (centavos) => {
  const sinal = centavos < 0 ? "-" : "";
  const absoluto = Math.abs(centavos);
  return `${sinal}${Math.floor(absoluto / 100)}.${String(absoluto % 100).padStart(2, "0")}`;
};

// Converte centavos para número com 2 casas, usado nas respostas JSON.
const paraNumero = (centavos) => centavos / 100;

// Lê um valor enviado pelo app (10, 10.5, "10,50" ou "10.50").
// Retorna os centavos ou null se o valor for inválido.
const lerValor = (valor) => {
  let textoValor;

  if (typeof valor === "number" && Number.isFinite(valor)) {
    textoValor = valor.toFixed(2);
    if (Math.abs(Number(textoValor) - valor) > 1e-9) {
      return null; // mais de 2 casas decimais
    }
  } else if (typeof valor === "string") {
    textoValor = valor.trim().replace(",", ".");
  } else {
    return null;
  }

  if (!/^\d{1,13}(\.\d{1,2})?$/.test(textoValor)) {
    return null;
  }

  return paraCentavos(textoValor);
};

module.exports = { paraCentavos, paraDecimal, paraNumero, lerValor };
