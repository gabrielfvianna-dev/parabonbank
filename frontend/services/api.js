
import * as SecureStore from "expo-secure-store";

// IP do computador na rede Wi-Fi.
// Não use localhost: o aplicativo roda no celular.
const API_URL = "http://172.20.10.6:3000";

export async function apiRequest(endpoint, options = {}) {
  const token = await SecureStore.getItemAsync("parabon_token");

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.message || "Não foi possível concluir a solicitação.");
  }

  return data;
}

export async function saveToken(token) {
  await SecureStore.setItemAsync("parabon_token", token);
}

export async function removeToken() {
  await SecureStore.deleteItemAsync("parabon_token");
}
