import { useRouter } from "expo-router";
import { useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import Button from "../components/Button";
import Input from "../components/Input";
import theme from "../constants/theme";

export default function Cadastro() {
  // Permite navegar entre as telas do aplicativo.
  const router = useRouter();

  // Estados dos dados pessoais.
  const [fullName, setFullName] = useState("");
  const [cpf, setCpf] = useState("");
  const [birthDate, setBirthDate] = useState("");

  // Estados dos dados de contato.
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  // Estados dos dados de segurança.
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");

  // Estado responsável pelo aceite dos termos.
  const [termsAccepted, setTermsAccepted] = useState(false);

  // Guarda as mensagens de erro de cada campo.
  const [errors, setErrors] = useState({});

  // Remove caracteres que não sejam números.
  const onlyNumbers = (value) => {
    return value.replace(/\D/g, "");
  };

  // Valida o CPF utilizando os dois dígitos verificadores.
  const validateCPF = (value) => {
    const numbers = onlyNumbers(value);

    // CPF precisa possuir exatamente 11 dígitos.
    if (numbers.length !== 11) {
      return false;
    }

    // Rejeita CPFs formados pelo mesmo número.
    if (/^(\d)\1{10}$/.test(numbers)) {
      return false;
    }

    // Calcula o primeiro dígito verificador.
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

    // Calcula o segundo dígito verificador.
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
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  };

  // Valida a data e verifica a idade mínima.
  const validateBirthDate = (value) => {
    // A data precisa seguir o padrão brasileiro DD-MM-AAAA.
    if (!/^\d{2}-\d{2}-\d{4}$/.test(value)) {
      return false;
    }

    // Separa dia, mês e ano.
    const [day, month, year] = value.split("-").map(Number);

    // Cria uma data usando os valores informados.
    const date = new Date(year, month - 1, day);

    // Verifica se a data realmente existe.
    if (
      date.getFullYear() !== year ||
      date.getMonth() + 1 !== month ||
      date.getDate() !== day
    ) {
      return false;
    }

    // Obtém a data atual.
    const today = new Date();

    // Calcula inicialmente a idade apenas pela diferença dos anos.
    let age = today.getFullYear() - year;

    // Verifica se o aniversário já aconteceu neste ano.
    const hasBirthdayPassed =
      today.getMonth() + 1 > month ||
      (today.getMonth() + 1 === month && today.getDate() >= day);

    // Se o aniversário ainda não aconteceu, reduz um ano da idade.
    if (!hasBirthdayPassed) {
      age--;
    }

    // O cadastro exige idade mínima de 18 anos.
    return age >= 18;
  };

  // Valida o formato básico de telefone brasileiro.
  const validatePhone = (value) => {
    const numbers = onlyNumbers(value);

    // Consideramos telefones brasileiros com 10 ou 11 dígitos.
    return numbers.length === 10 || numbers.length === 11;
  };

  // Valida as regras definidas para a senha.
  const validatePassword = (value) => {
    // A senha precisa possuir entre 8 e 64 caracteres.
    if (value.length < 8 || value.length > 64) {
      return false;
    }

    // Precisa possuir uma letra maiúscula.
    if (!/[A-Z]/.test(value)) {
      return false;
    }

    // Precisa possuir uma letra minúscula.
    if (!/[a-z]/.test(value)) {
      return false;
    }

    // Precisa possuir um número.
    if (!/\d/.test(value)) {
      return false;
    }

    // Precisa possuir um caractere especial.
    if (!/[^A-Za-z0-9]/.test(value)) {
      return false;
    }

    return true;
  };

  // Valida as regras básicas do PIN.
  const validatePin = (value) => {
    // O PIN precisa possuir exatamente 6 dígitos.
    if (!/^\d{6}$/.test(value)) {
      return false;
    }

    // Rejeita PINs formados pelo mesmo número.
    if (/^(\d)\1{5}$/.test(value)) {
      return false;
    }

    // Rejeita sequências crescentes, como 123456.
    if (value === "123456") {
      return false;
    }

    // Rejeita sequências decrescentes, como 654321.
    if (value === "654321") {
      return false;
    }

    return true;
  };

  const validateField = (field) => {
    // Cria uma cópia dos erros atuais.
    const newErrors = { ...errors };

    // Verifica especificamente o campo informado.
    switch (field) {
      case "fullName":
        if (fullName.trim().length < 3) {
          newErrors.fullName = "Informe seu nome completo.";
        } else {
          delete newErrors.fullName;
        }
        break;

      case "cpf":
        if (!validateCPF(cpf)) {
          newErrors.cpf = "Informe um CPF válido.";
        } else {
          delete newErrors.cpf;
        }
        break;

      case "birthDate":
        if (!validateBirthDate(birthDate)) {
          newErrors.birthDate =
            "Informe uma data válida e tenha pelo menos 18 anos.";
        } else {
          delete newErrors.birthDate;
        }
        break;

      case "email":
        if (!validateEmail(email.trim())) {
          newErrors.email = "Informe um e-mail válido.";
        } else {
          delete newErrors.email;
        }
        break;

      case "phone":
        if (!validatePhone(phone)) {
          newErrors.phone = "Informe um telefone válido.";
        } else {
          delete newErrors.phone;
        }
        break;

      case "password":
        if (!validatePassword(password)) {
          newErrors.password =
            "A senha deve ter 8–64 caracteres, com maiúscula, minúscula, número e caractere especial.";
        } else {
          delete newErrors.password;
        }
        break;

      case "confirmPassword":
        if (password !== confirmPassword) {
          newErrors.confirmPassword = "As senhas não são iguais.";
        } else {
          delete newErrors.confirmPassword;
        }
        break;

      case "pin":
        if (!validatePin(pin)) {
          newErrors.pin =
            "O PIN deve ter 6 dígitos e não pode ser uma sequência ou repetição.";
        } else {
          delete newErrors.pin;
        }
        break;

      case "confirmPin":
        if (pin !== confirmPin) {
          newErrors.confirmPin = "Os PINs não são iguais.";
        } else {
          delete newErrors.confirmPin;
        }
        break;

      default:
        break;
    }

    // Atualiza os erros exibidos na tela.
    setErrors(newErrors);
  };

  // Executa todas as validações do formulário.
  const handleRegister = () => {
    // Começamos com um objeto vazio para armazenar os erros.
    const newErrors = {};

    // Validação do nome.
    if (fullName.trim().length < 3) {
      newErrors.fullName = "Informe seu nome completo.";
    }

    // Validação do CPF.
    if (!validateCPF(cpf)) {
      newErrors.cpf = "Informe um CPF válido.";
    }

    // Validação da data de nascimento.
    if (!validateBirthDate(birthDate)) {
      newErrors.birthDate =
        "Informe uma data válida e tenha pelo menos 18 anos.";
    }

    // Validação do e-mail.
    if (!validateEmail(email.trim())) {
      newErrors.email = "Informe um e-mail válido.";
    }

    // Validação do telefone.
    if (!validatePhone(phone)) {
      newErrors.phone = "Informe um telefone válido.";
    }

    // Validação da senha.
    if (!validatePassword(password)) {
      newErrors.password =
        "A senha deve ter 8–64 caracteres, com maiúscula, minúscula, número e caractere especial.";
    }

    // Confirmação da senha.
    if (password !== confirmPassword) {
      newErrors.confirmPassword = "As senhas não são iguais.";
    }

    // Validação do PIN.
    if (!validatePin(pin)) {
      newErrors.pin =
        "O PIN deve ter 6 dígitos e não pode ser uma sequência ou repetição.";
    }

    // Confirmação do PIN.
    if (pin !== confirmPin) {
      newErrors.confirmPin = "Os PINs não são iguais.";
    }

    // Aceite dos termos.
    if (!termsAccepted) {
      newErrors.terms = "Aceite os termos para continuar.";
    }

    // Atualiza os erros exibidos na tela.
    setErrors(newErrors);

    // Se existir pelo menos um erro, interrompe o cadastro.
    if (Object.keys(newErrors).length > 0) {
      return;
    }

    // Ainda não enviamos os dados para o backend.
    Alert.alert(
      "Cadastro",
      "Dados validados com sucesso. A conexão com o servidor será implementada na próxima etapa.",
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

      {/* Título da tela */}
      <View style={styles.headerContainer}>
        <Text style={styles.title}>Crie sua conta</Text>

        <Text style={styles.subtitle}>
          Preencha seus dados para começar a usar o Parabon Bank.
        </Text>
      </View>

      {/* Dados pessoais */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Dados pessoais</Text>

        <Input
          label="Nome completo"
          value={fullName}
          onChangeText={setFullName}
          placeholder="Digite seu nome completo"
          autoCapitalize="words"
          error={errors.fullName}
        />

        <Input
          label="CPF"
          value={cpf}
          onChangeText={setCpf}
          placeholder="Digite seu CPF"
          keyboardType="numeric"
          error={errors.cpf}
        />

        <Input
          label="Data de nascimento"
          value={birthDate}
          onChangeText={setBirthDate}
          placeholder="DD-MM-AAAA"
          keyboardType="numeric"
          error={errors.birthDate}
          onBlur={() => validateField("birthDate")}
        />
      </View>

      {/* Dados de contato */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Dados de contato</Text>

        <Input
          label="E-mail"
          value={email}
          onChangeText={setEmail}
          placeholder="Digite seu e-mail"
          keyboardType="email-address"
          error={errors.email}
        />

        <Input
          label="Telefone"
          value={phone}
          onChangeText={setPhone}
          placeholder="Digite seu telefone"
          keyboardType="phone-pad"
          error={errors.phone}
        />
      </View>

      {/* Dados de segurança */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Segurança</Text>

        <Input
          label="Senha"
          value={password}
          onChangeText={setPassword}
          placeholder="Digite sua senha"
          secureTextEntry
          error={errors.password}
        />

        <Input
          label="Confirmar senha"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          placeholder="Digite sua senha novamente"
          secureTextEntry
          error={errors.confirmPassword}
        />

        <Input
          label="PIN"
          value={pin}
          onChangeText={setPin}
          placeholder="Digite seu PIN de 6 dígitos"
          secureTextEntry
          keyboardType="numeric"
          error={errors.pin}
        />

        <Input
          label="Confirmar PIN"
          value={confirmPin}
          onChangeText={setConfirmPin}
          placeholder="Digite seu PIN novamente"
          secureTextEntry
          keyboardType="numeric"
          error={errors.confirmPin}
        />
      </View>

      {/* Aceite dos termos */}
      <Pressable
        style={styles.termsContainer}
        onPress={() => setTermsAccepted(!termsAccepted)}
      >
        <View
          style={[
            styles.checkbox,
            termsAccepted && styles.checkboxSelected,
            errors.terms && styles.checkboxError,
          ]}
        >
          {termsAccepted && <Text style={styles.checkmark}>✓</Text>}
        </View>

        <Text style={styles.termsText}>
          Li e aceito os termos de uso e a política de privacidade.
        </Text>
      </Pressable>

      {/* Mensagem relacionada aos termos */}
      {errors.terms && <Text style={styles.termsError}>{errors.terms}</Text>}

      {/* Botão principal */}
      <View style={styles.buttonContainer}>
        <Button title="Criar conta" onPress={handleRegister} />
      </View>

      {/* Voltar para o Login */}
      <View style={styles.loginContainer}>
        <Text style={styles.loginText}>Já possui uma conta?</Text>

        <Button
          title="Voltar para o login"
          variant="secondary"
          onPress={() => router.push("/login")}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: theme.colors.cream,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
  },

  brandContainer: {
    alignItems: "center",
    marginBottom: theme.spacing.lg,
  },

  brand: {
    color: theme.colors.burgundy,
    fontSize: 32,
    fontWeight: theme.fontWeight.bold,
    letterSpacing: 3,
  },

  bank: {
    color: theme.colors.wine,
    fontSize: theme.fontSize.medium,
    fontWeight: theme.fontWeight.medium,
    letterSpacing: 5,
  },

  headerContainer: {
    marginBottom: theme.spacing.xl,
  },

  title: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.title,
    fontWeight: theme.fontWeight.bold,
    marginBottom: theme.spacing.sm,
  },

  subtitle: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.medium,
    lineHeight: 24,
  },

  section: {
    marginBottom: theme.spacing.lg,
  },

  sectionTitle: {
    color: theme.colors.burgundy,
    fontSize: theme.fontSize.large,
    fontWeight: theme.fontWeight.bold,
    marginBottom: theme.spacing.md,
  },

  termsContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: theme.spacing.sm,
  },

  checkbox: {
    width: 24,
    height: 24,
    borderWidth: theme.borderWidth.thin,
    borderColor: theme.colors.roseDust,
    borderRadius: theme.radius.small,
    backgroundColor: theme.colors.white,
    alignItems: "center",
    justifyContent: "center",
    marginRight: theme.spacing.sm,
  },

  checkboxSelected: {
    backgroundColor: theme.colors.burgundy,
    borderColor: theme.colors.burgundy,
  },

  checkboxError: {
    borderColor: theme.colors.wine,
    borderWidth: theme.borderWidth.medium,
  },

  checkmark: {
    color: theme.colors.white,
    fontSize: 16,
    fontWeight: theme.fontWeight.bold,
  },

  termsText: {
    flex: 1,
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    lineHeight: 20,
  },

  termsError: {
    color: theme.colors.wine,
    fontSize: theme.fontSize.small,
    marginBottom: theme.spacing.md,
  },

  buttonContainer: {
    width: "100%",
    marginBottom: theme.spacing.lg,
  },

  loginContainer: {
    alignItems: "center",
  },

  loginText: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    marginBottom: theme.spacing.sm,
  },
});
