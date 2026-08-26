import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/manager/",
  plugins: [react()],
  server: {
    proxy: {
      "/manager/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/manager/, ""),
      },
      "/manager/ws": {
        target: "ws://localhost:8000",
        ws: true,
        rewrite: (path) => path.replace(/^\/manager/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
