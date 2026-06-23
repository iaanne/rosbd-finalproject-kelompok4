import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://fastapi:8000',
      '/ws': {
        target: 'ws://fastapi:8000',
        ws: true,
      },
    },
  },
})
