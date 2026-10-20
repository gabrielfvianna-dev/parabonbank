
import { useRouter } from "expo-router";
import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";

import Button from "../components/Button";
import Input from "../components/Input";
import theme from "../constants/theme";

// Mantém somente os números do identificador.
const onlyNumbers = (value) => value.replace(/\D/g, "");

// Valida o formato básico de e-mail.
const validateEmail = (value) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
};

// Valida o CPF e seus dígitos verificadores.
const validateCPF = (value) => {
  const cpf = onlyNumbers(value);

  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
    return false;
  }

  for (let position = 9; position <= 10; position++) {
    let sum = 0;

    for (let i = 0; i < position; i++) {
      sum += Number(cpf[i]) * (position + 1 - i);
    }

    const remainder = (sum * 10) % 11;
    const digit = remainder === 10 ? 0 : remainder;

    if (digit !== Number(cpf[position])) {
      return false;
    }
  }

  return true;
};

export default function Login() {
  // Permite navegar entre as telas.
  const router = useRouter();

  // Armazena os valores digitados.
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  // Valida os campos antes de continuar.
  const handleLogin = () => {
    const value = identifier.trim();

    // Verifica se o identificador foi preenchido.
    if (!value) {
      Alert.alert("Atenção", "Informe seu e-mail ou CPF.");
      return;
    }

    // Aceita um e-mail válido ou um CPF válido.
    const isValidIdentifier =
      validateEmail(value) || validateCPF(value);

    if (!isValidIdentifier) {
      Alert.alert(
        "Atenção",
        "Informe um e-mail válido ou um CPF válido.",
      );
      return;
    }

    // Verifica se a senha foi preenchida.
    if (!password) {
      Alert.alert("Atenção", "Informe sua senha.");
      return;
    }

    // A autenticação real será feita pela API futuramente.
    Alert.alert(
      "Login",
      "A validação foi concluída. A conexão com o servidor será implementada na próxima etapa.",
    );
  };

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      {/* Identidade visual do Parabon Bank */}
      <View style={styles.brandContainer}>
        <Text style={styles.brand}>PARABON</Text>
        <Text style={styles.bank}>BANK</Text>
      </View>

      {/* Título e descrição */}
      <View style={styles.headerContainer}>
        <Text style={styles.title}>Acesse sua conta</Text>

        <Text style={styles.subtitle}>
          Entre para acessar os serviços do Parabon Bank.
        </Text>
      </View>

      {/* Formulário de login */}
      <View style={styles.formContainer}>
        <Input
          label="E-mail ou CPF"
          value={identifier}
          onChangeText={setIdentifier}
          placeholder="Digite seu e-mail ou CPF"
        />

        <Input
          label="Senha"
          value={password}
          onChangeText={setPassword}
          placeholder="Digite sua senha"
          secureTextEntry
        />

        <Button title="Entrar" onPress={handleLogin} />
      </View>

      {/* Área para criação de uma nova conta */}
      <View style={styles.registerContainer}>
        <Text style={styles.registerText}>
          Ainda não possui uma conta?
        </Text>

        <Button
          title="Criar conta"
          variant="secondary"
          onPress={() => router.push("/cadastro")}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Container principal da tela.
  container: {
    flexGrow: 1,
    backgroundColor: theme.colors.cream,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
    justifyContent: "center",
  },

  // Área que contém o nome da instituição.
  brandContainer: {
    alignItems: "center",
    marginBottom: theme.spacing.xl,
  },

  // Texto principal da marca.
  brand: {
    color: theme.colors.burgundy,
    fontSize: 32,
    fontWeight: theme.fontWeight.bold,
    letterSpacing: 3,
  },

  // Texto secundário da marca.
  bank: {
    color: theme.colors.wine,
    fontSize: theme.fontSize.medium,
    fontWeight: theme.fontWeight.medium,
    letterSpacing: 5,
  },

  // Área do título e subtítulo.
  headerContainer: {
    marginBottom: theme.spacing.xl,
  },

  // Título principal da tela.
  title: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.title,
    fontWeight: theme.fontWeight.bold,
    marginBottom: theme.spacing.sm,
  },

  // Texto explicativo abaixo do título.
  subtitle: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.medium,
    lineHeight: 24,
  },

  // Área dos campos e botão.
  formContainer: {
    width: "100%",
  },

  // Área inferior relacionada ao cadastro.
  registerContainer: {
    marginTop: theme.spacing.xl,
    alignItems: "center",
  },

  // Texto acima do botão de cadastro.
  registerText: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    marginBottom: theme.spacing.sm,
  },
});
