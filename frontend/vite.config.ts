import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
// Dev-only proxy: /api → Flask. AVENTRA_API_PROXY overrides the target when port 5000 is taken locally.
// (The former /market-api → Yahoo proxy was removed: market data now comes from Flask at /api/market/*.)
export default defineConfig({ plugins: [react(), tailwindcss()], server: { proxy: { '/api': { target: process.env.AVENTRA_API_PROXY ?? 'http://127.0.0.1:5000', changeOrigin: true } } } })
