import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    watch: {
      usePolling: true,
    },
    hmr: {
      clientPort: 5173,
    },
    proxy: {
      '/api/webhook': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:5678', // Default local n8n port, overridden by Docker
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/webhook/, '/webhook/insurance-ocr-openrouter'),
      },
    },
  },
})
