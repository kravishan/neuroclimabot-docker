import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react-swc'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@services': resolve(__dirname, 'src/services'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@constants': resolve(__dirname, 'src/constants'),
      '@styles': resolve(__dirname, 'src/styles'),
      '@assets': resolve(__dirname, 'src/assets'),
    },
  },
  server: {
    allowedHosts: [
      'localhost',
      '128-214-253-121.nip.io'
    ],
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
    },
    proxy: {
      // Proxy API requests to the FastAPI backend (Server)
      '/server': {
        target: process.env.VITE_SERVER_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/server/, ''),
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('[Vite Proxy] Error connecting to server:', err.message);
            console.log('[Vite Proxy] Server proxy target:', options.target);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('[Vite Proxy] Request to server:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('[Vite Proxy] Response from server:', proxyRes.statusCode, req.url);
          });
        },
      },
      // Proxy processor requests to the Document Processor service
      '/processor': {
        target: process.env.VITE_PROCESSOR_PROXY_TARGET || 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/processor/, ''),
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('[Vite Proxy] Error connecting to processor:', err.message);
            console.log('[Vite Proxy] Processor proxy target:', options.target);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('[Vite Proxy] Request to processor:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('[Vite Proxy] Response from processor:', proxyRes.statusCode, req.url);
          });
        },
      },
    },
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['lucide-react'],
          i18n: ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
          utils: ['axios', 'd3'],
        },
      },
    },
  },
})