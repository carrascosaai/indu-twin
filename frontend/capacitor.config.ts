import type { CapacitorConfig } from "@capacitor/cli";

// La app Android es una capa nativa fina alrededor de la web ya publicada
// en Vercel: no empaqueta los assets localmente, así que cada actualización
// del sitio se ve en la app sin publicar un APK nuevo. Las llamadas al
// backend son same-origin (la WebView navega a indu-twin.vercel.app), asi
// que no hace falta tocar CORS_ORIGINS para esto.
const config: CapacitorConfig = {
  appId: "com.indutwin.app",
  appName: "INDU-TWIN",
  webDir: "dist",
  server: {
    url: "https://indu-twin.vercel.app",
    androidScheme: "https",
  },
};

export default config;
