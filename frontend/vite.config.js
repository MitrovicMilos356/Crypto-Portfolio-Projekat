import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // u developmentu Flask radi na 5000, pa /api prosledjujemo njemu.
    // changeOrigin: false cuva originalni Host (localhost:3000), da bi Google prijava
    // vratila korisnika na dev server, a ne direktno na Flask
    proxy: {
      '/api': { target: 'http://127.0.0.1:5000', changeOrigin: false },
    },
  },
})
