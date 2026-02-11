import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.test.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{js,ts,vue}'],
      exclude: ['src/**/*.d.ts', 'src/**/*.test.*', 'src/main.js']
    },
    setupFiles: ['./src/test/setup.js'],
    testTimeout: 10000
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  }
})
