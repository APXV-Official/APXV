import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      // API only — do not proxy UI routes (/pipeline, /jobs, etc.)
      "/health": {
        target: "http://127.0.0.1:8741",
        changeOrigin: true,
      },
      "/api": {
        target: "http://127.0.0.1:8741",
        changeOrigin: true,
      },
    },
  },
});