import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({ plugins: [react(), tailwindcss()], server: { proxy: { '/market-api': { target: 'https://query1.finance.yahoo.com', changeOrigin: true, rewrite: (path) => path.replace(/^\/market-api/, '') }, '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true } } } })
