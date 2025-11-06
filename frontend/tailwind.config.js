/**
 * ============================================================================
 * TAILWIND CSS CONFIGURATION - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   Tailwind CSS framework configuration.
 *
 * WHAT IS TAILWIND?
 *   Utility-first CSS framework. Provides low-level utility classes
 *   like "p-4", "text-blue-600", "flex", etc.
 *
 *   INSTEAD OF:
 *     .card {
 *       padding: 1rem;
 *       background: white;
 *       border-radius: 0.5rem;
 *     }
 *
 *   YOU WRITE:
 *     <div className="p-4 bg-white rounded-lg">
 *
 * BENEFITS:
 *   - Fast development (no naming classes)
 *   - Consistent design system
 *   - Small bundle size (only used classes)
 *   - Responsive by default
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

/** @type {import('tailwindcss').Config} */
export default {
  /**
   * Content Paths
   *
   * Tailwind scans these files to find used classes.
   * Only used classes are included in final CSS (tree-shaking).
   */
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  /**
   * Theme Customization
   *
   * Extend or override Tailwind's default theme.
   */
  theme: {
    extend: {
      /**
       * Custom Colors
       *
       * Add your brand colors here.
       * Example: "bg-brand-500", "text-brand-700"
       */
      colors: {
        // Brand colors (example - customize as needed)
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',  // Primary brand color
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },

      /**
       * Custom Fonts
       *
       * Add custom font families here.
       */
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'Consolas',
          'Monaco',
          'monospace',
        ],
      },

      /**
       * Custom Spacing
       *
       * Add custom spacing values if needed.
       * Tailwind has good defaults (0.5rem increments).
       */
      spacing: {
        // Example: "p-18" = padding: 4.5rem
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      /**
       * Custom Animation
       *
       * Add custom animations for loading states, etc.
       */
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },

      /**
       * Custom Box Shadow
       *
       * Add custom shadow styles.
       */
      boxShadow: {
        'inner-lg': 'inset 0 2px 4px 0 rgb(0 0 0 / 0.1)',
      },
    },
  },

  /**
   * Plugins
   *
   * Extend Tailwind with additional functionality.
   */
  plugins: [
    // Add Tailwind plugins here
    // Example: require('@tailwindcss/forms')
  ],
}
