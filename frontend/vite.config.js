import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI backend so the browser can use
// relative URLs (works from any preview host).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Accept any preview host the platform proxies us through
    allowedHosts: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
