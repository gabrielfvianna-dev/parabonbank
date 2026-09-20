import colors from "./colors";

const theme = {
  // Cores da identidade visual do aplicativo.
  colors,

  // Espaçamentos utilizados para manter consistência
  // entre os diferentes componentes da interface.
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },

  // Tamanhos de texto padronizados.
  fontSize: {
    small: 14,
    medium: 16,
    large: 20,
    title: 28,
  },

  // Pesos de fonte utilizados na interface.
  fontWeight: {
    regular: "400",
    medium: "500",
    bold: "700",
  },

  // Arredondamento dos componentes.
  radius: {
    small: 8,
    medium: 12,
    large: 16,
    pill: 999,
  },

  // Espessuras de borda.
  borderWidth: {
    thin: 1,
    medium: 2,
  },
};

export default theme;
