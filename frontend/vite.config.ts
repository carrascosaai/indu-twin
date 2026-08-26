import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
  build: {
    // Three.js/@react-three (vista 3D) y Leaflet (mapa) ya se cargan bajo
    // demanda via React.lazy en DashboardPage — sus chunks son grandes
    // porque las librerias lo son, no porque falte separarlos del bundle
    // principal. Se sube el umbral para no generar un aviso enganoso sobre
    // algo que ya esta resuelto.
    chunkSizeWarningLimit: 1100,
  },
})
