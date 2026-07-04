import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// Absolute, not relative: a relative `root` resolves against process.cwd(), not
// this config file's location, so `vite --config frontend/vite.config.js` run
// from the repo root would otherwise treat the repo root as the project root.
const frontendDir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  root: frontendDir,
  test: {
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['lcov', 'text'],
      include: ['src/**/*.{js,vue}'],
      exclude: [
        'src/main.js',
        'src/router/**',
        'src/sw.js',
        'src/components/HelloWorld.vue',
      ],
    },
  },
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      registerType: 'prompt',
      devOptions: {
        enabled: true,
        type: 'module',
      },
      includeAssets: ['favicon.svg', 'icons/apple-touch-icon.png', 'icons/icon-192.png', 'icons/icon-512.png'],
      manifest: {
        name: 'Meridian — Where Ideas Converge',
        short_name: 'Meridian',
        description: 'A blog where curious minds explore technology, culture, and ideas that matter.',
        theme_color: '#1e1b4b',
        background_color: '#0f0e1a',
        display: 'standalone',
        orientation: 'portrait-primary',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:3000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:3003', changeOrigin: true },
    },
  },
})
