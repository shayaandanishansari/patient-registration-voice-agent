import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// `npm run build:backend` uses mode "embedded": the build the FastAPI backend
// serves at /dashboard/ (see backend/app/routers/dashboard.py). That bundle is
// committed and public, so it must never carry VITE_API_KEY from .env.local,
// and it talks to whichever server it was loaded from.
export default defineConfig(({ mode }) => {
  const embedded = mode === "embedded";
  return {
    base: embedded ? "/dashboard/" : "/",
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    define: embedded
      ? {
          "import.meta.env.VITE_API_KEY": JSON.stringify(""),
          "import.meta.env.VITE_API_BASE_URL": JSON.stringify(""),
        }
      : {},
    build: embedded
      ? { outDir: "../backend/assets/dashboard", emptyOutDir: true }
      : {},
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
