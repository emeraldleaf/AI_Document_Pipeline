/**
 * ============================================================================
 * TYPE DEFINITIONS - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   TypeScript type definitions for the document search application.
 *   Ensures type safety across the frontend and matches backend API contracts.
 *
 * WHY TYPESCRIPT?
 *   - Catch bugs at compile time (before users see them)
 *   - Better IDE autocomplete and IntelliSense
 *   - Self-documenting code (types show what data looks like)
 *   - Refactoring safety (compiler catches breaking changes)
 *
 * ORGANIZATION:
 *   1. Search-related types (SearchMode, SearchRequest, SearchResponse)
 *   2. Document types (SearchResult, Document)
 *   3. Statistics types (Stats, CategoryStats)
 *   4. UI state types
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

// ==========================================================================
// SEARCH TYPES
// ==========================================================================

/**
 * Search mode determines how we search documents
 *
 * KEYWORD:
 *   - Fast traditional search (like Ctrl+F)
 *   - Matches exact words/phrases
 *   - Best for: Known terms, IDs, names
 *   - Example: "invoice-2024-001"
 *
 * SEMANTIC:
 *   - AI-powered meaning-based search
 *   - Understands context and concepts
 *   - Best for: Questions, concepts, fuzzy matches
 *   - Example: "documents about payment terms"
 *
 * HYBRID:
 *   - Combines both keyword + semantic
 *   - Balanced approach (best of both worlds)
 *   - Best for: General purpose search
 *   - Example: Most user searches
 */
export type SearchMode = 'keyword' | 'semantic' | 'hybrid';

/**
 * Request parameters for document search
 *
 * This matches the FastAPI backend's search endpoint parameters.
 * All fields are optional except 'query'.
 */
export interface SearchRequest {
  /** The search query string (e.g., "invoice payment terms") */
  query: string;

  /** Search mode (defaults to 'hybrid') */
  mode?: SearchMode;

  /** Filter by document category (e.g., "invoice", "contract") */
  category?: string;

  /** Maximum results to return (defaults to 20) */
  limit?: number;

  /** Pagination offset (defaults to 0) */
  offset?: number;
}

/**
 * Document metadata from the API
 *
 * Contains file information and timestamps
 */
export interface DocumentMetadata {
  file_name: string;
  file_type: string;
  file_size: number;
  created_date: string | null;
  modified_date: string | null;
  page_count: number | null;
}

/**
 * A single search result with all metadata
 *
 * IMPORTANT FIELDS:
 *   - id: Unique document identifier (use for downloads/previews)
 *   - combined_score: Relevance score (higher = better match)
 *   - content_preview: Matching text snippet (show user why it matched)
 *   - download_url: Direct link to download original file
 */
export interface SearchResult {
  /** Unique document ID */
  id: number;

  /** Original filename */
  file_name: string;

  /** Document category (invoice, contract, receipt, etc.) */
  category: string;

  /** File path */
  file_path: string;

  /** Search scores */
  keyword_rank: number;
  semantic_rank: number;
  combined_score: number;

  /** Content preview text */
  content_preview: string;

  /** File metadata */
  metadata: DocumentMetadata;

  /** Download URLs */
  download_url: string;
  preview_url: string;
}

/**
 * Response from search API endpoint
 *
 * Contains results + metadata (total count, timing, etc.)
 */
export interface SearchResponse {
  /** Search query */
  query: string;

  /** Search mode used */
  mode: SearchMode;

  /** Array of matching documents */
  results: SearchResult[];

  /** Total number of matching documents (for pagination) */
  total_results: number;

  /** Number of results returned in this response */
  returned_results: number;

  /** Current page offset */
  offset: number;

  /** Max results per page */
  limit: number;

  /** How long the search took (milliseconds) */
  execution_time_ms: number;
}

// ==========================================================================
// DOCUMENT TYPES
// ==========================================================================

/**
 * Detailed document information
 *
 * Used when viewing a single document's full details
 * (not just search results).
 */
export interface Document extends SearchResult {
  /** Additional fields that might be in detail view */
  // For now, same as SearchResult
  // Can extend later with more fields
}

// ==========================================================================
// STATISTICS TYPES
// ==========================================================================

/**
 * Document count per category
 *
 * Example:
 *   {
 *     "invoice": 1250,
 *     "contract": 342,
 *     "receipt": 891
 *   }
 */
export interface CategoryStats {
  [category: string]: number;
}

/**
 * Overall system statistics
 *
 * Displayed in the stats panel to give users
 * an overview of the document collection.
 */
export interface Stats {
  /** Total documents indexed */
  total_documents: number;

  /** Documents per category */
  categories: CategoryStats;

  /** Average processing time per document (milliseconds) */
  avg_processing_time_ms: number;

  /** Total storage used (bytes) */
  total_storage_bytes: number;

  /** Most recent document timestamp */
  last_updated: string;  // ISO 8601 format

  /** System health status */
  status: 'healthy' | 'degraded' | 'down';
}

// ==========================================================================
// UI STATE TYPES
// ==========================================================================

/**
 * Loading state for async operations
 */
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

/**
 * Sort options for search results
 */
export type SortBy = 'relevance' | 'date' | 'filename' | 'category';
export type SortOrder = 'asc' | 'desc';

/**
 * Filter state for search
 */
export interface SearchFilters {
  /** Selected category (undefined = all categories) */
  category?: string;

  /** Date range filter */
  dateFrom?: Date;
  dateTo?: Date;

  /** File type filter */
  fileTypes?: string[];

  /** Minimum confidence score */
  minConfidence?: number;
}

/**
 * Pagination state
 */
export interface PaginationState {
  /** Current page (0-indexed) */
  page: number;

  /** Results per page */
  pageSize: number;

  /** Total number of results */
  totalResults: number;

  /** Total number of pages */
  totalPages: number;
}

// ==========================================================================
// ERROR TYPES
// ==========================================================================

/**
 * API error response
 *
 * Matches FastAPI's error response format
 */
export interface ApiError {
  /** Error message for display */
  detail: string;

  /** HTTP status code */
  status_code: number;

  /** Error type/code for handling */
  error_code?: string;
}

// ==========================================================================
// UTILITY TYPES
// ==========================================================================

/**
 * Generic async data wrapper
 *
 * Useful for components that display async data with loading/error states
 */
export interface AsyncData<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * File upload state
 */
export interface UploadProgress {
  /** File being uploaded */
  file: File;

  /** Upload progress (0-100) */
  progress: number;

  /** Upload status */
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';

  /** Error message if failed */
  error?: string;
}

/**
 * Preview modal state
 */
export interface PreviewState {
  /** Whether modal is open */
  isOpen: boolean;

  /** Document being previewed */
  document: SearchResult | null;

  /** Loading state */
  loading: boolean;
}
