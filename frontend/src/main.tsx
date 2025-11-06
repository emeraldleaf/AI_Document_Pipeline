/**
 * ============================================================================
 * MAIN ENTRY POINT - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   Application entry point. Sets up React, React Query, and renders the app.
 *
 * RESPONSIBILITIES:
 *   1. Import global CSS (Tailwind)
 *   2. Set up React Query provider
 *   3. Render root App component
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

/**
 * React Query Client Configuration
 *
 * WHAT IS REACT QUERY?
 *   - Data fetching and caching library
 *   - Automatically handles loading states, errors, retries
 *   - Background data updates
 *   - Optimistic UI updates
 *
 * CONFIGURATION:
 *   - defaultOptions: Apply to all queries
 *   - staleTime: How long data is considered fresh (default: 0)
 *   - cacheTime: How long unused data stays in cache (default: 5 min)
 *   - retry: Auto-retry failed requests
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retry failed requests once (avoid hammering broken API)
      retry: 1,

      // Refetch on window focus (useful for long-running sessions)
      refetchOnWindowFocus: false,

      // Default stale time: 0 (always refetch)
      // Individual queries can override this
      staleTime: 0,
    },
  },
});

/**
 * Render the React application
 *
 * REACT 18 FEATURES:
 *   - Concurrent rendering (better performance)
 *   - Automatic batching (fewer re-renders)
 *   - StrictMode: Helps catch bugs in development
 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
