import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI server, so the browser only ever talks to one address (no CORS).
// allowedHosts lets a Cloudflare Tunnel hostname reach the dev/preview server.
const proxy = { "/api": "http://127.0.0.1:8000" };
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy, allowedHosts: true },
  preview: { port: 5173, proxy, allowedHosts: true },
});
