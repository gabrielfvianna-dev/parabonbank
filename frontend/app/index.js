import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import Button from "../components/Button";
import theme from "../constants/theme";

export default function Index() {
  // Permite navegar entre as telas do aplicativo.
  const router = useRouter();

  return (
    <View style={styles.container}>
      {/* Identidade visual do Parabon Bank */}
      <View style={styles.brandContainer}>
        <Text style={styles.brand}>PARABON</Text>

        <Text style={styles.bank}>BANK</Text>
      </View>

      {/* Mensagem principal da tela inicial */}
      <Text style={styles.title}>
        Simplicidade e confiança para cuidar do seu dinheiro.
      </Text>

      {/* Botões principais de acesso */}
      <View style={styles.buttonsContainer}>
        <Button title="Entrar" onPress={() => router.push("/login")} />

        <Button
          title="Criar conta"
          variant="secondary"
          onPress={() => router.push("/cadastro")}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.cream,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
    justifyContent: "space-between",
  },

  brandContainer: {
    alignItems: "center",
    marginTop: theme.spacing.xl,
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

  title: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.large,
    fontWeight: theme.fontWeight.medium,
    textAlign: "center",
    lineHeight: 30,
    paddingHorizontal: theme.spacing.md,
  },

  buttonsContainer: {
    width: "100%",
    gap: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
});
