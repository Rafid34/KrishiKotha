import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// envDir points to the repo root; /api is proxied to the backend in dev.
export default defineConfig({
  plugins: [react()],
  envDir: '..',
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  preview: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'node',
    include: ['src/__tests__/**/*.test.{js,jsx}'],
  },
});
