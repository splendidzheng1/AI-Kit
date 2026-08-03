import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 部署到 GitHub Pages 子目录 AI-Kit/03-Home-Debt，需设置 base 让所有静态资源路径带上前缀
  base: '/AI-Kit/03-Home-Debt/',
  plugins: [vue()],
  server: {
    host: true,
    allowedHosts: ['1089560gz6wu7.vicp.fun']
  }
})
