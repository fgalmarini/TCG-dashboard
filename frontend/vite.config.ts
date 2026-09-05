import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const eventHost = process.env.TCG_EVENT_HOST?.trim()

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    allowedHosts: eventHost ? ['localhost', '127.0.0.1', eventHost] : undefined,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
      },
    },
  },
})
