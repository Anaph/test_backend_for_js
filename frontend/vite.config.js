import { defineConfig } from 'vite';

export default defineConfig({
  server: { port: 5173, proxy: { '/auth': 'http://127.0.0.1:8000', '/stream': { target: 'ws://127.0.0.1:8000', ws: true } } }
});
