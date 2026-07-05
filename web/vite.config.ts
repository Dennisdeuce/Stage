import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      // Precache the self-hosted fonts and placeholder art for offline use.
      workbox: { globPatterns: ["**/*.{js,css,html,svg,png,woff2}"] },
      manifest: {
        id: "/",
        lang: "en-US",
        categories: ["entertainment", "music"],
        name: "PNW Stage",
        short_name: "PNW Stage",
        description: "Concerts & comedy across the Pacific Northwest, refreshed daily.",
        theme_color: "#0B0F0D",
        background_color: "#0B0F0D",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
        ]
      }
    })
  ]
});
