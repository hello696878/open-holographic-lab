import { defineConfig } from 'vite';

export default defineConfig({
  base: '/',
  cacheDir: '.vite',
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false, target: 'es2022' },
});
