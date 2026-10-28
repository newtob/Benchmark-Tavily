import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    tailwindcss(),
    // SvelteKit 3 reads its config from this plugin call; svelte.config.js
    // is no longer supported.
    sveltekit({
      preprocess: vitePreprocess(),
      // Compiles to plain static files served by nginx — no Node runtime in
      // the final Docker stage. See specs/tavily-benchmark-app.md §5/§8.
      adapter: adapter({
        pages: "build",
        assets: "build",
        fallback: undefined,
        precompress: false,
        strict: true,
      }),
    }),
  ],
  server: {
    proxy: {
      // Local dev: forward /api to a uvicorn instance run separately
      // (`just py-dev` or equivalent) — mirrors nginx's prod routing.
      "/api": "http://127.0.0.1:8000",
    },
  },
});
