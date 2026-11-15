import { useEffect, useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  Pressable,
  ActivityIndicator,
} from "react-native";

import theme from "../constants/theme";
import { apiRequest } from "../services/api";

export default function Dashboard() {
  const [showBalance, setShowBalance] = useState(true);

  const [cliente, setCliente] = useState(null);
  const [conta, setConta] = useState(null);
  const [transactions, setTransactions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Formata valores numéricos para o padrão monetário brasileiro.
  const formatCurrency = (value) => {
    return Number(value || 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  };

  // Busca os dados do cliente, conta e extrato.
  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const dadosCliente = await apiRequest("/api/clientes/me");

      setCliente(dadosCliente.cliente);

      const contaPrincipal = dadosCliente.contas?.[0];

      if (!contaPrincipal) {
        setConta(null);
        setTransactions([]);
        return;
      }

      setConta(contaPrincipal);

      const dadosExtrato = await apiRequest(
        `/api/contas/${contaPrincipal.id}/extrato?limit=50`
      );

      setTransactions(dadosExtrato.transacoes || []);
    } catch (err) {
      setError(err.message || "Não foi possível carregar os dados.");
    } finally {
      setLoading(false);
    }
  };

  // Executa a busca quando a tela é aberta.
  useEffect(() => {
    loadDashboard();
  }, []);

  const balance = formatCurrency(conta?.balance);

  const shortcuts = [
    { id: "1", symbol: "⇄", title: "Pix" },
    { id: "2", symbol: "▤", title: "Extrato" },
    { id: "3", symbol: "◎", title: "Face Payment" },
  ];

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Cabeçalho */}
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>PARABON BANK</Text>

          <Text style={styles.greeting}>
            Olá, {cliente?.fullName?.split(" ")[0] || "cliente"}!
          </Text>

          <Text style={styles.subtitle}>
            Seja bem-vindo à sua conta.
          </Text>
        </View>

        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {cliente?.fullName?.charAt(0)?.toUpperCase() || "U"}
          </Text>
        </View>
      </View>

      {/* Cartão de saldo */}
      <View style={styles.balanceCard}>
        <View style={styles.balanceHeader}>
          <Text style={styles.balanceLabel}>Saldo disponível</Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              showBalance ? "Ocultar saldo" : "Mostrar saldo"
            }
            onPress={() => setShowBalance(!showBalance)}
          >
            <Text style={styles.balanceAction}>
              {showBalance ? "Ocultar" : "Mostrar"}
            </Text>
          </Pressable>
        </View>

        <Text style={styles.balanceValue}>
          {showBalance ? balance : "R$ ••••••"}
        </Text>

        <Text style={styles.balanceNote}>
          {conta
            ? `Conta ${conta.accountNumber}-${conta.accountDigit}`
            : "Informações da conta"}
        </Text>
      </View>

      {/* Atalhos */}
      <Text style={styles.sectionTitle}>Acesso rápido</Text>

      <View style={styles.shortcuts}>
        {shortcuts.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={item.title}
            onPress={() => {}}
            style={({ pressed }) => [
              styles.shortcut,
              pressed && styles.pressed,
            ]}
          >
            <View style={styles.shortcutIcon}>
              <Text style={styles.shortcutSymbol}>{item.symbol}</Text>
            </View>

            <Text style={styles.shortcutTitle}>{item.title}</Text>
          </Pressable>
        ))}
      </View>

      {/* Movimentações */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Últimas movimentações</Text>
      </View>

      <View style={styles.transactionsCard}>
        {loading ? (
          <View style={{ padding: 24, alignItems: "center" }}>
            <ActivityIndicator color={theme.colors.burgundy} />
            <Text style={{ marginTop: 10, color: theme.colors.espresso }}>
              Carregando informações...
            </Text>
          </View>
        ) : error ? (
          <View style={{ padding: 16, alignItems: "center" }}>
            <Text style={{ color: theme.colors.wine, textAlign: "center" }}>
              {error}
            </Text>

            <Pressable onPress={loadDashboard} style={{ marginTop: 12 }}>
              <Text style={styles.balanceAction}>Tentar novamente</Text>
            </Pressable>
          </View>
        ) : transactions.length === 0 ? (
          <View style={{ padding: 20 }}>
            <Text style={{ color: theme.colors.espresso, textAlign: "center" }}>
              Nenhuma movimentação encontrada.
            </Text>
          </View>
        ) : (
          transactions.map((transaction, index) => (
            <View key={transaction.id}>
              {index > 0 && <View style={styles.separator} />}

              <View style={styles.transaction}>
                <View style={styles.transactionIcon}>
                  <Text style={styles.transactionSymbol}>•</Text>
                </View>

                <View style={styles.transactionInfo}>
                  <Text style={styles.transactionTitle}>
                    {transaction.type}
                  </Text>

                  <Text style={styles.transactionDescription}>
                    {transaction.description || "Movimentação bancária"}
                  </Text>
                </View>

                <Text style={styles.transactionAmount}>
                  {formatCurrency(transaction.amount)}
                </Text>
              </View>
            </View>
          ))
        )}
      </View>

      <Text style={styles.footer}>
        Parabon Bank · Protótipo acadêmico
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: theme.colors.cream,
  },

  content: {
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.xl,
    paddingBottom: theme.spacing.xl,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: theme.spacing.lg,
  },

  brand: {
    color: theme.colors.wine,
    fontSize: theme.fontSize.small,
    fontWeight: theme.fontWeight.bold,
    letterSpacing: 2,
    marginBottom: theme.spacing.sm,
  },

  greeting: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.title,
    fontWeight: theme.fontWeight.bold,
  },

  subtitle: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    marginTop: theme.spacing.xs,
  },

  avatar: {
    width: 48,
    height: 48,
    borderRadius: theme.radius.pill,
    backgroundColor: theme.colors.roseDust,
    alignItems: "center",
    justifyContent: "center",
  },

  avatarText: {
    color: theme.colors.burgundy,
    fontSize: theme.fontSize.large,
    fontWeight: theme.fontWeight.bold,
  },

  balanceCard: {
    backgroundColor: theme.colors.burgundy,
    borderRadius: theme.radius.large,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
  },

  balanceHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  balanceLabel: {
    color: theme.colors.cream,
    fontSize: theme.fontSize.small,
  },

  balanceAction: {
    color: theme.colors.roseDust,
    fontSize: theme.fontSize.small,
    fontWeight: theme.fontWeight.medium,
  },

  balanceValue: {
    color: theme.colors.white,
    fontSize: 30,
    fontWeight: theme.fontWeight.bold,
    marginTop: theme.spacing.md,
  },

  balanceNote: {
    color: theme.colors.roseDust,
    fontSize: 12,
    marginTop: theme.spacing.sm,
  },

  sectionTitle: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.large,
    fontWeight: theme.fontWeight.bold,
  },

  shortcuts: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },

  shortcut: {
    flex: 1,
    alignItems: "center",
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.xs,
    backgroundColor: theme.colors.white,
    borderRadius: theme.radius.large,
  },

  shortcutIcon: {
    width: 44,
    height: 44,
    borderRadius: theme.radius.pill,
    backgroundColor: theme.colors.cream,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: theme.spacing.sm,
  },

  shortcutSymbol: {
    color: theme.colors.burgundy,
    fontSize: 26,
    fontWeight: theme.fontWeight.bold,
  },

  shortcutTitle: {
    color: theme.colors.espresso,
    fontSize: 12,
    fontWeight: theme.fontWeight.medium,
    textAlign: "center",
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },

  demoLabel: {
    color: theme.colors.wine,
    fontSize: 10,
    fontWeight: theme.fontWeight.bold,
    letterSpacing: 1,
  },

  transactionsCard: {
    backgroundColor: theme.colors.white,
    borderRadius: theme.radius.large,
    paddingHorizontal: theme.spacing.md,
  },

  transaction: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: theme.spacing.md,
    gap: theme.spacing.sm,
  },

  transactionIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },

  incomeIcon: {
    backgroundColor: "#E2F3E8",
  },

  expenseIcon: {
    backgroundColor: "#F5E3E4",
  },

  transactionSymbol: {
    color: theme.colors.espresso,
    fontSize: 22,
    fontWeight: theme.fontWeight.bold,
  },

  transactionInfo: {
    flex: 1,
  },

  transactionTitle: {
    color: theme.colors.espresso,
    fontSize: theme.fontSize.small,
    fontWeight: theme.fontWeight.bold,
  },

  transactionDescription: {
    color: theme.colors.espresso,
    fontSize: 11,
    marginTop: theme.spacing.xs,
  },

  transactionAmount: {
    fontSize: 12,
    fontWeight: theme.fontWeight.bold,
  },

  incomeText: {
    color: "#247A45",
  },

  expenseText: {
    color: theme.colors.wine,
  },

  separator: {
    height: 1,
    backgroundColor: theme.colors.cream,
  },

  footer: {
    color: theme.colors.espresso,
    fontSize: 11,
    textAlign: "center",
    marginTop: theme.spacing.xl,
  },

  pressed: {
    opacity: 0.75,
  },
});
