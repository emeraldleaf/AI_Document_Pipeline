/**
 * ============================================================================
 * POSTCSS CONFIGURATION - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   PostCSS configuration for processing CSS with Tailwind.
 *
 * WHAT IS POSTCSS?
 *   A tool for transforming CSS with JavaScript plugins.
 *   Think of it like Babel for CSS.
 *
 * WHY NEEDED?
 *   - Tailwind CSS requires PostCSS to work
 *   - Autoprefixer adds vendor prefixes for browser compatibility
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

export default {
  plugins: {
    /**
     * Tailwind CSS Plugin
     *
     * Processes @tailwind directives and generates utility classes.
     */
    tailwindcss: {},

    /**
     * Autoprefixer Plugin
     *
     * Automatically adds vendor prefixes for browser compatibility.
     *
     * EXAMPLE:
     *   Input:  display: flex;
     *   Output: display: -webkit-box;
     *           display: -ms-flexbox;
     *           display: flex;
     */
    autoprefixer: {},
  },
}
