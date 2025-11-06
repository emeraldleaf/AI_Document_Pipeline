/**
 * ============================================================================
 * VITE CONFIGURATION - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   Vite build tool configuration for the React frontend.
 *
 * WHAT IS VITE?
 *   Modern build tool and dev server for frontend projects.
 *
 *   WHY VITE?
 *     - Lightning fast hot module replacement (HMR)
 *     - Instant server start (no bundling in dev)
 *     - Optimized production builds
 *     - Native ES modules
 *     - Better than Webpack/Create React App
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Vite Configuration
 *
 * See: https://vitejs.dev/config/
 */
export default defineConfig({
  /**
   * Plugins
   *
   * - react: Enables React Fast Refresh (HMR for React)
   */
  plugins: [react()],

  /**
   * Development Server Configuration
   */
  server: {
    port: 3000, // Dev server port (http://localhost:3000)
    open: true, // Auto-open browser on server start

    /**
     * Proxy API requests to backend
     *
     * WHY PROXY?
     *   - Avoids CORS issues in development
     *   - Frontend and backend can run on different ports
     *   - Requests to /api/* are forwarded to FastAPI backend
     *
     * EXAMPLE:
     *   Frontend:  http://localhost:3000/api/search
     *   Proxied to: http://localhost:8000/api/search
     */
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // FastAPI backend (use IPv4 explicitly)
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  /**
   * Build Configuration
   */
  build: {
    outDir: 'dist', // Output directory for production build
    sourcemap: true, // Generate source maps for debugging
    minify: 'terser', // Minification (terser is best)

    /**
     * Rollup Options (Vite uses Rollup under the hood)
     */
    rollupOptions: {
      output: {
        /**
         * Manual chunks for better caching
         *
         * Splits vendor code (React, libraries) from app code.
         * When you update your app, users don't re-download React.
         */
        manualChunks: {
          // React and React DOM in one chunk
          react: ['react', 'react-dom'],

          // React Query in separate chunk
          'react-query': ['@tanstack/react-query'],

          // HTTP client
          axios: ['axios'],

          // Icons
          icons: ['lucide-react'],
        },
      },
    },
  },

  /**
   * Optimize Dependencies
   *
   * Pre-bundle dependencies for faster dev server start
   */
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@tanstack/react-query',
      'axios',
      'lucide-react',
    ],
  },
});
