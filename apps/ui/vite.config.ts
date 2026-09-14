import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    proxy: {
      // Local dev: forward /api to a uvicorn instance run separately
      // (`just py-dev` or equivalent) — mirrors nginx's prod routing.
      "/api": "http://127.0.0.1:8000",
    },
  },
});
