const app = require("./app");
const config = require("./config");

// "0.0.0.0" permite que o celular (Expo Go) acesse a API pela rede local.
app.listen(config.port, "0.0.0.0", () => {
  console.log(`API do Parabon Bank rodando em http://localhost:${config.port}`);

  if (config.habilitarRotasDev) {
    console.warn("ATENÇÃO: rotas de desenvolvimento (/api/dev) habilitadas.");
  }
});
