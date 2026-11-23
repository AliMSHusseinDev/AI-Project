import { defineConfig } from "vite";
const api = process.env.AI_PROJECT_API_ORIGIN || "http://127.0.0.1:8000";
export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: !process.env.AI_PROJECT_API_ORIGIN,
    proxy: { "/api": api },
  },
  preview: { proxy: { "/api": api } },
});
