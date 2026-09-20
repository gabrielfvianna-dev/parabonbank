import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import theme from "../constants/theme";

const Button = ({
  title,
  onPress,
  disabled = false,
  loading = false,
  variant = "primary",
}) => {
  // O botão fica desabilitado durante o carregamento
  // ou quando a propriedade disabled estiver ativada.
  const isDisabled = disabled || loading;

  // Define o estilo visual de acordo com a variante escolhida.
  const buttonStyle =
    variant === "secondary" ? styles.secondaryButton : styles.primaryButton;

  const textStyle =
    variant === "secondary" ? styles.secondaryText : styles.primaryText;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        buttonStyle,
        pressed && styles.pressed,
        isDisabled && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={
            variant === "secondary" ? theme.colors.burgundy : theme.colors.white
          }
        />
      ) : (
        <Text style={[styles.text, textStyle]}>{title}</Text>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    width: "100%",
    minHeight: 52,
    borderRadius: theme.radius.medium,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: theme.spacing.lg,
  },

  primaryButton: {
    backgroundColor: theme.colors.burgundy,
  },

  secondaryButton: {
    backgroundColor: theme.colors.cream,
    borderWidth: theme.borderWidth.thin,
    borderColor: theme.colors.burgundy,
  },

  text: {
    fontSize: theme.fontSize.medium,
    fontWeight: theme.fontWeight.bold,
  },

  primaryText: {
    color: theme.colors.white,
  },

  secondaryText: {
    color: theme.colors.burgundy,
  },

  pressed: {
    opacity: 0.8,
  },

  disabled: {
    opacity: 0.5,
  },
});

export default Button;
