import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
    watch: {
      // The backend shares this repo root, so its writes land inside Vite's
      // watch scope. The SQLite journal is touched on every decision, which
      // full-page-reloaded the storefront thousands of times per session —
      // long enough to lose the session id and its buffered events with it.
      ignored: [
        '**/data/**',
        '**/.venv/**',
        '**/__pycache__/**',
        '**/backend/**',
        '**/ml/**',
        '**/alembic/**',
        '**/scripts/**',
        '**/tests/**',
        '**/*.db',
        '**/*.db-journal',
        '**/*.db-wal',
        '**/*.db-shm',
      ],
    },
  },
})
