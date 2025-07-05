import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      // 这里是关键配置：
      // 我们告诉 Vite，所有以 '@' 开头的导入路径，
      // 都应该映射到 './src' 这个实际的物理路径。
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})