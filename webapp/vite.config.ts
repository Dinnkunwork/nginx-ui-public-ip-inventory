import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { nginxUiPlugin } from '@nginxui/plugin-sdk/vite'

export default defineConfig({
  plugins: [
    vue(),
    nginxUiPlugin({
      id: 'com.company.public-ip-inventory',
      entry: 'src/main.ts',
      outDir: 'dist',
    }),
  ],
})
