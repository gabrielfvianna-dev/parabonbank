import { StyleSheet, Text, TextInput, View } from "react-native";

import theme from "../constants/theme";

const Input = ({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry = false,
  keyboardType = "default",
  autoCapitalize = "none",
  error = "",
}) => {
  // Verifica se existe alguma mensagem de erro para o campo.
  const hasError = Boolean(error);

  return (
    <View style={styles.container}>
      {/* Nome do campo */}
      <Text style={styles.label}>{label}</Text>

      {/* Campo onde o usuário digita a informação */}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        style={[styles.input, hasError && styles.inputError]}
      />

      {/* Mensagem de erro exibida abaixo do campo */}
      {hasError && <Text style={styles.errorText}>{error}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  // Espaçamento geral do componente.
  container: {
    width: "100%",
    marginBottom: theme.spacing.md,
  },

  // Texto que identifica o campo.
  label: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    fontWeight: theme.fontWeight.medium,
    marginBottom: theme.spacing.sm,
  },

  // Aparência padrão do campo.
  input: {
    width: "100%",
    minHeight: 52,
    borderWidth: theme.borderWidth.thin,
    borderColor: theme.colors.roseDust,
    borderRadius: theme.radius.medium,
    backgroundColor: theme.colors.white,
    color: theme.colors.espresso,
    fontSize: theme.fontSize.medium,
    paddingHorizontal: theme.spacing.md,
  },

  // Aparência do campo quando existe um erro.
  inputError: {
    borderColor: theme.colors.wine,
    borderWidth: theme.borderWidth.medium,
  },

  // Texto apresentado abaixo de um campo inválido.
  errorText: {
    color: theme.colors.wine,
    fontSize: theme.fontSize.small,
    marginTop: theme.spacing.xs,
  },
});

export default Input;
