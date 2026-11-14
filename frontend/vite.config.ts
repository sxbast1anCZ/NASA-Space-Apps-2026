import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The API runs on port 8000 in development: uvicorn backend.main:app --reload
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
