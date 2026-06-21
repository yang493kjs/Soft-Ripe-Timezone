import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue({
    template: {
      compilerOptions: {
        isCustomElement: tagName => {
          return tagName === 'vue-advanced-chat' || tagName === 'emoji-picker'
        }
      }
    }
  })],
  server: {
    proxy: {
      '/api': 'http://localhost:8765',
      '/avatars': 'http://localhost:8765',
      '/static': 'http://localhost:8765'
    }
  }
})
