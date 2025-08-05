import { fileURLToPath, URL } from 'node:url'
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    strictPort: true,
    cors: true,
    hmr: {
      host: "localhost",
    },
    allowedHosts: ["localhost", "127.0.0.1", "studio.tesslate.com"],
  },
})
