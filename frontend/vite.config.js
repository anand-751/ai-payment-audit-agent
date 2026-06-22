import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload-payment-batch': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/run-audit': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/batches': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
