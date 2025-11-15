/**
 * ============================================================================
 * DOCUMENT SEARCH UI - Main Application Component
 * ============================================================================
 *
 * PURPOSE:
 *   High-performance React application for document search with:
 *   - Real-time search as you type (debounced)
 *   - Multiple search modes (keyword, semantic, hybrid)
 *   - Document preview and download
 *   - Responsive design (mobile-friendly)
 *   - Loading states and error handling
 *   - Pagination for large result sets
 *
 * ARCHITECTURE:
 *   React 18 + TypeScript + TanStack Query + Tailwind CSS
 *   - React Query: Data fetching, caching, background updates
 *   - TypeScript: Type safety, better DX
 *   - Tailwind: Utility-first CSS, responsive design
 *   - Vite: Fast build tool and HMR
 *
 * PERFORMANCE OPTIMIZATIONS:
 *   1. Debounced search (avoid API spam)
 *   2. React Query caching (instant results for repeat searches)
 *   3. Lazy loading (load results as needed)
 *   4. Optimistic updates (instant UI feedback)
 *   5. Memoization (prevent unnecessary re-renders)
 *
 * KEY FEATURES:
 *   - Search with keyword/semantic/hybrid modes
 *   - Real-time results with <300ms latency
 *   - Document preview in modal
 *   - Download original files
 *   - Category filtering
 *   - Pagination
 *   - Mobile responsive
 *
 * RELATED FILES:
 *   - api/main.py - FastAPI backend
 *   - src/types.ts - TypeScript type definitions
 *   - src/api.ts - API client functions
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Search, FileText, Filter,
  Zap, Brain, TrendingUp, Clock, AlertCircle,
  ChevronLeft, ChevronRight, Upload
} from 'lucide-react';
import { searchDocuments, getStats } from './api';
import { SearchMode } from './types';
import SearchResultCard from './components/SearchResultCard';
import SearchFilters from './components/SearchFilters';
import StatsPanel from './components/StatsPanel';
import { BatchUpload } from './components/BatchUpload';
import { debounce } from './utils';

type View = 'search' | 'batch-upload';

function App() {
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================

  const [currentView, setCurrentView] = useState<View>('search');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [page, setPage] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  const RESULTS_PER_PAGE = 20;

  // ==========================================================================
  // DEBOUNCED SEARCH
  // ==========================================================================

  // Debounce search input to avoid API spam
  // Only search after user stops typing for 300ms
  const debouncedSetQuery = useCallback(
    debounce((value: string) => {
      setDebouncedQuery(value);
      setPage(0); // Reset to first page on new search
    }, 300),
    []
  );

  useEffect(() => {
    debouncedSetQuery(query);
  }, [query, debouncedSetQuery]);

  // ==========================================================================
  // DATA FETCHING WITH TANSTACK QUERY (React Query)
  // ==========================================================================
  //
  // WHAT IS TANSTACK QUERY?
  //   A powerful data-fetching library that handles:
  //   - Caching (same request = use cache, no API call)
  //   - Loading states (no need for useState)
  //   - Error handling (automatic retry on failure)
  //   - Background updates (keep data fresh)
  //   - Request deduplication (multiple components, one API call)
  //
  // WHY USE IT?
  //   WITHOUT TanStack Query:
  //     - 20+ lines of code per API call (useState, useEffect, error handling)
  //     - No caching (same request = multiple API calls)
  //     - Manual loading/error state management
  //
  //   WITH TanStack Query:
  //     - 5 lines of code
  //     - Automatic caching
  //     - Automatic loading/error states
  //
  // LEARN MORE:
  //   - Official Docs: https://tanstack.com/query/latest/docs/framework/react/installation
  //   - Our Guide: frontend/TANSTACK_QUERY_GUIDE.md
  //
  // ==========================================================================

  /**
   * QUERY 1: Search Documents
   *
   * PURPOSE:
   *   Fetch documents matching the user's search query.
   *
   * HOW IT WORKS:
   *   1. User types "invoice" in search box
   *   2. Debounced to 300ms (avoid API spam)
   *   3. useQuery automatically calls searchDocuments()
   *   4. Results cached for 5 minutes
   *   5. If user searches "invoice" again within 5 min → instant results (cache)
   *
   * QUERY KEY:
   *   ['search', debouncedQuery, searchMode, selectedCategory, page]
   *
   *   WHY INCLUDE ALL PARAMETERS?
   *     - When ANY parameter changes, it creates a NEW query key
   *     - New query key = new API call
   *     - Different query keys = different cache entries
   *
   *   EXAMPLES:
   *     ['search', 'invoice', 'hybrid', undefined, 0]  <- Cache entry 1
   *     ['search', 'invoice', 'keyword', undefined, 0] <- Cache entry 2 (different mode)
   *     ['search', 'contract', 'hybrid', undefined, 0] <- Cache entry 3 (different query)
   *
   * RETURN VALUES:
   *   - data: The search results (undefined while loading)
   *   - isLoading: true during FIRST fetch (show spinner)
   *   - isFetching: true during ANY fetch including background (show subtle indicator)
   *   - error: Error object if fetch failed
   *
   * CACHING BEHAVIOR:
   *   - staleTime: 5 minutes
   *     * Data is "fresh" for 5 minutes
   *     * Searches within 5 min use cache (instant!)
   *     * After 5 min, data becomes "stale"
   *     * Next search will refetch, but shows cached data first (UX++)
   *
   *   - gcTime: 30 minutes (default, not specified)
   *     * After component unmounts, cache stays for 30 min
   *     * If user returns within 30 min, cache is available
   *     * After 30 min, cache is garbage collected
   *
   * CONDITIONAL FETCHING:
   *   - enabled: debouncedQuery.length > 0
   *     * Query only runs if user has entered a search term
   *     * Empty search = no API call
   *
   * ERROR HANDLING:
   *   - retry: 1
   *     * If API call fails, automatically retry once
   *     * Useful for temporary network issues
   *     * After 1 retry, shows error state
   */
  const {
    data: searchResults,
    isLoading: isSearching,
    error: searchError,
    isFetching
  } = useQuery({
    // QUERY KEY - Uniquely identifies this query and its cache
    // When any of these values change, a new API call is made
    queryKey: ['search', debouncedQuery, searchMode, selectedCategory, page],

    // QUERY FUNCTION - Fetches the data
    // Must return a Promise (our API functions use axios, which returns Promises)
    queryFn: () => searchDocuments({
      query: debouncedQuery,
      mode: searchMode,
      category: selectedCategory,
      limit: RESULTS_PER_PAGE,
      offset: page * RESULTS_PER_PAGE
    }),

    // ENABLED - Only run query if we have a search term
    // Without this, query would run on mount even with empty string
    enabled: debouncedQuery.length > 0,

    // STALE TIME - How long data is considered "fresh" (5 minutes)
    // Fresh data won't be refetched (uses cache)
    // After 5 min, data becomes stale and will refetch on next use
    staleTime: 5 * 60 * 1000,

    // RETRY - Retry failed requests once
    // Helps with temporary network issues
    retry: 1
  });

  /**
   * QUERY 2: System Statistics
   *
   * PURPOSE:
   *   Fetch and display system statistics (total documents, categories, etc.)
   *
   * HOW IT WORKS:
   *   1. Query runs immediately on mount (no dependencies)
   *   2. Results cached for 30 seconds
   *   3. Auto-refreshes every 60 seconds (refetchInterval)
   *   4. Always shows latest stats without user action
   *
   * QUERY KEY:
   *   ['stats']
   *
   *   Simple key with no parameters (stats are global, not user-specific)
   *
   * POLLING (Auto-Refresh):
   *   - refetchInterval: 60 * 1000 (60 seconds)
   *     * TanStack Query automatically refetches every minute
   *     * Keeps stats dashboard up-to-date
   *     * User sees new documents appear without refreshing page
   *
   * CACHING:
   *   - staleTime: 30 seconds
   *     * Stats are fresh for 30 seconds
   *     * Multiple components using stats = one API call
   *     * After 30 sec, next access triggers refetch
   *
   * WHY SHORTER STALE TIME?
   *   Stats change more frequently than search results
   *   (new documents being processed in background)
   *
   * EXAMPLE TIMELINE:
   *   0:00 - Component mounts → API call → Cache stats
   *   0:30 - Stats become stale (but still in cache)
   *   1:00 - Auto-refetch (refetchInterval) → Update cache
   *   2:00 - Auto-refetch → Update cache
   *   ... continues every minute
   */
  const { data: stats } = useQuery({
    // QUERY KEY - Simple key for global stats
    queryKey: ['stats'],

    // QUERY FUNCTION - Fetch stats from API
    queryFn: getStats,

    // STALE TIME - Data fresh for 30 seconds
    // Short stale time = more frequent updates
    staleTime: 30 * 1000,

    // REFETCH INTERVAL - Auto-refresh every minute
    // Keeps dashboard stats current without user action
    // Even if user isn't actively searching, stats stay updated
    refetchInterval: 60 * 1000
  });

  // ==========================================================================
  // EVENT HANDLERS
  // ==========================================================================

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Search happens automatically via debounced query
  };

  const handleModeChange = (mode: SearchMode) => {
    setSearchMode(mode);
    setPage(0); // Reset pagination
  };

  const handleCategoryChange = (category: string | undefined) => {
    setSelectedCategory(category);
    setPage(0); // Reset pagination
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ==========================================================================
  // DERIVED STATE
  // ==========================================================================

  const hasResults = searchResults && searchResults.results.length > 0;
  const showPagination = searchResults && searchResults.total_results > RESULTS_PER_PAGE;
  const totalPages = searchResults ? Math.ceil(searchResults.total_results / RESULTS_PER_PAGE) : 0;

  // ==========================================================================
  // RENDER
  // ==========================================================================

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                <FileText className="inline-block w-8 h-8 mr-2 text-blue-600" />
                Document Search
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Powered by AI • {stats?.total_documents.toLocaleString() || 0} documents indexed
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Navigation Tabs */}
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentView('search')}
                  className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                    currentView === 'search'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
                <button
                  onClick={() => setCurrentView('batch-upload')}
                  className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                    currentView === 'batch-upload'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  Batch Upload
                </button>
              </div>

              {/* Stats Button (only show in search view) */}
              {currentView === 'search' && (
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-2"
                >
                  <Filter className="w-4 h-4" />
                  {showFilters ? 'Hide' : 'Show'} Filters
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Stats Panel (collapsible) */}
      {currentView === 'search' && showFilters && stats && (
        <StatsPanel stats={stats} />
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Batch Upload View */}
        {currentView === 'batch-upload' && (
          <BatchUpload />
        )}

        {/* Search View */}
        {currentView === 'search' && (
          <div>
        {/* Search Bar */}
        <div className="mb-8">
          <form onSubmit={handleSearch} className="relative">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search documents... (e.g., 'invoice payment terms', 'Q3 financial report')"
                className="w-full pl-12 pr-4 py-4 text-lg border-2 border-gray-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
                autoFocus
              />
              {isFetching && (
                <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                </div>
              )}
            </div>

            {/* Search Mode Tabs */}
            <div className="mt-4 flex gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => handleModeChange('keyword')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  searchMode === 'keyword'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-400'
                }`}
              >
                <Zap className="w-4 h-4" />
                <span className="font-medium">Keyword</span>
                <span className="text-xs opacity-75">(Fast)</span>
              </button>

              <button
                type="button"
                onClick={() => handleModeChange('semantic')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  searchMode === 'semantic'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-400'
                }`}
              >
                <Brain className="w-4 h-4" />
                <span className="font-medium">Semantic</span>
                <span className="text-xs opacity-75">(Smart)</span>
              </button>

              <button
                type="button"
                onClick={() => handleModeChange('hybrid')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  searchMode === 'hybrid'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-400'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                <span className="font-medium">Hybrid</span>
                <span className="text-xs opacity-75">(Balanced)</span>
              </button>
            </div>
          </form>

          {/* Category Filter */}
          {showFilters && stats && (
            <SearchFilters
              categories={Object.keys(stats.categories)}
              selectedCategory={selectedCategory}
              onCategoryChange={handleCategoryChange}
            />
          )}
        </div>

        {/* Search Results */}
        <div className="space-y-6">
          {/* Results Header */}
          {hasResults && (
            <div className="flex items-center justify-between text-sm text-gray-600">
              <div className="flex items-center gap-4">
                <span>
                  Found <strong className="text-gray-900">{searchResults.total_results.toLocaleString()}</strong> results
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {searchResults.execution_time_ms.toFixed(0)}ms
                </span>
              </div>
              <div>
                Page {page + 1} of {totalPages}
              </div>
            </div>
          )}

          {/* Loading State */}
          {isSearching && (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-gray-600">Searching documents...</p>
            </div>
          )}

          {/* Error State */}
          {searchError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900">Search Failed</h3>
                <p className="text-red-700 mt-1">
                  {searchError instanceof Error ? searchError.message : 'An error occurred while searching'}
                </p>
              </div>
            </div>
          )}

          {/* Empty State (No Query) */}
          {!query && !isSearching && (
            <div className="text-center py-20">
              <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Start searching</h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Enter keywords or ask questions to search across all your documents.
                Try different search modes for best results.
              </p>
            </div>
          )}

          {/* No Results */}
          {query && !isSearching && !hasResults && !searchError && (
            <div className="text-center py-20">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Try using different keywords or switch search modes.
                Semantic search works better for questions and concepts.
              </p>
            </div>
          )}

          {/* Results List */}
          {hasResults && !isSearching && (
            <div className="space-y-4">
              {searchResults.results.map((result) => (
                <SearchResultCard
                  key={result.id}
                  result={result}
                  searchMode={searchMode}
                  query={debouncedQuery}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {showPagination && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  const pageNum = page < 3 ? i : page - 2 + i;
                  if (pageNum >= totalPages) return null;

                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      className={`px-4 py-2 rounded-lg transition-colors ${
                        pageNum === page
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum + 1}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
        </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-20 py-8 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-600 text-sm">
          <p>AI Document Classification Pipeline • Built with React + FastAPI + PostgreSQL</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
