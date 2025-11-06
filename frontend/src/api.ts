/**
 * ============================================================================
 * API CLIENT - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   Centralized API client for communicating with the FastAPI backend.
 *   All HTTP requests go through these functions.
 *
 * WHY CENTRALIZED?
 *   - Single source of truth for API endpoints
 *   - Easy to add authentication, retries, logging
 *   - Type-safe requests/responses
 *   - Consistent error handling
 *
 * ARCHITECTURE:
 *   - Uses axios for HTTP requests
 *   - Base URL configurable via environment variable
 *   - Returns typed responses (TypeScript)
 *   - Handles errors consistently
 *
 * USAGE EXAMPLE:
 *   import { searchDocuments } from './api';
 *
 *   const results = await searchDocuments({
 *     query: 'invoice',
 *     mode: 'hybrid',
 *     limit: 20
 *   });
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  SearchRequest,
  SearchResponse,
  Document,
  Stats,
  ApiError
} from './types';

// ==========================================================================
// CONFIGURATION
// ==========================================================================

/**
 * API base URL
 *
 * DEVELOPMENT: Direct connection to backend (http://127.0.0.1:8000)
 *   - Using IPv4 address explicitly to avoid IPv6 issues
 *   - CORS is configured on backend to allow localhost:3000
 * PRODUCTION: Set via VITE_API_URL environment variable
 *
 * To configure for production:
 *   - Create .env.local file in frontend directory
 *   - Add: VITE_API_URL=http://your-api-server:8000
 *   - Vite will automatically load it
 */
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

/**
 * Axios instance with default configuration
 *
 * FEATURES:
 *   - Base URL set to API server
 *   - 30 second timeout (adjust for slow networks)
 *   - JSON content type headers
 *   - Automatic retry on network errors (handled by React Query)
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==========================================================================
// ERROR HANDLING
// ==========================================================================

/**
 * Transforms axios errors into user-friendly error messages
 *
 * HANDLES:
 *   - Network errors (server down, no internet)
 *   - API errors (400, 404, 500, etc.)
 *   - Timeout errors
 *   - Unknown errors
 *
 * @param error - Axios error object
 * @returns User-friendly error message
 */
function handleApiError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;

    // Server responded with error status
    if (axiosError.response) {
      const { status, data } = axiosError.response;

      // Use server's error message if available
      const message = data?.detail || `Server error: ${status}`;

      throw new Error(message);
    }

    // Request made but no response (network error, timeout)
    if (axiosError.request) {
      if (axiosError.code === 'ECONNABORTED') {
        throw new Error('Request timeout - server is taking too long to respond');
      }
      throw new Error('Cannot connect to server - please check your internet connection');
    }
  }

  // Unknown error
  throw new Error('An unexpected error occurred');
}

// ==========================================================================
// SEARCH API
// ==========================================================================

/**
 * Search for documents
 *
 * ENDPOINT: GET /api/search
 *
 * PARAMETERS:
 *   - query: Search string (required)
 *   - mode: 'keyword' | 'semantic' | 'hybrid' (default: 'hybrid')
 *   - category: Filter by category (optional)
 *   - limit: Results per page (default: 20, max: 100)
 *   - offset: Pagination offset (default: 0)
 *
 * RETURNS:
 *   - results: Array of matching documents
 *   - total_results: Total matches (for pagination)
 *   - execution_time_ms: How long search took
 *
 * EXAMPLE:
 *   const response = await searchDocuments({
 *     query: 'invoice payment terms',
 *     mode: 'semantic',
 *     limit: 20
 *   });
 *   console.log(`Found ${response.total_results} documents`);
 */
export async function searchDocuments(
  params: SearchRequest
): Promise<SearchResponse> {
  try {
    const response = await apiClient.get<SearchResponse>('/api/search', {
      params: {
        q: params.query,
        mode: params.mode || 'hybrid',
        category: params.category,
        limit: params.limit || 20,
        offset: params.offset || 0,
      },
    });

    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
}

// ==========================================================================
// DOCUMENT API
// ==========================================================================

/**
 * Get detailed information for a specific document
 *
 * ENDPOINT: GET /api/documents/{id}
 *
 * PARAMETERS:
 *   - id: Document ID (from search results)
 *
 * RETURNS:
 *   - Full document details with all metadata
 *
 * EXAMPLE:
 *   const doc = await getDocument('abc123');
 *   console.log(doc.filename, doc.category);
 */
export async function getDocument(id: string): Promise<Document> {
  try {
    const response = await apiClient.get<Document>(`/api/documents/${id}`);
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
}

/**
 * Get document preview text
 *
 * ENDPOINT: GET /api/preview/{id}
 *
 * PARAMETERS:
 *   - id: Document ID
 *
 * RETURNS:
 *   - Extracted text content (first 5000 chars)
 *
 * EXAMPLE:
 *   const preview = await getDocumentPreview('abc123');
 *   // Display in modal
 */
export async function getDocumentPreview(id: string): Promise<string> {
  try {
    const response = await apiClient.get<{ content: string; preview_length: number }>(
      `/api/preview/${id}`
    );
    return response.data.content;
  } catch (error) {
    return handleApiError(error);
  }
}

/**
 * Get download URL for a document
 *
 * ENDPOINT: GET /api/download/{id}
 *
 * NOTE: This doesn't download the file directly.
 * Use this URL in a link or window.open() to trigger download.
 *
 * PARAMETERS:
 *   - id: Document ID
 *
 * RETURNS:
 *   - Full URL to download endpoint
 *
 * EXAMPLE:
 *   const url = getDownloadUrl('abc123');
 *   // <a href={url} download>Download</a>
 */
export function getDownloadUrl(id: string): string {
  return `${API_BASE_URL}/api/download/${id}`;
}

/**
 * Download a document (triggers browser download)
 *
 * Opens the download URL in a new window, which triggers
 * the browser's download dialog.
 *
 * PARAMETERS:
 *   - id: Document ID
 *
 * EXAMPLE:
 *   downloadDocument('abc123');
 *   // Browser shows download dialog
 */
export function downloadDocument(id: string): void {
  const url = getDownloadUrl(id);
  window.open(url, '_blank');
}

// ==========================================================================
// STATISTICS API
// ==========================================================================

/**
 * Get system statistics
 *
 * ENDPOINT: GET /api/stats
 *
 * RETURNS:
 *   - total_documents: Count of indexed documents
 *   - categories: Document counts per category
 *   - avg_processing_time_ms: Average processing time
 *   - total_storage_bytes: Total storage used
 *   - last_updated: Most recent document timestamp
 *   - status: System health status
 *
 * EXAMPLE:
 *   const stats = await getStats();
 *   console.log(`${stats.total_documents} documents indexed`);
 */
export async function getStats(): Promise<Stats> {
  try {
    const response = await apiClient.get<Stats>('/api/stats');
    return response.data;
  } catch (error) {
    return handleApiError(error);
  }
}

// ==========================================================================
// HEALTH CHECK API
// ==========================================================================

/**
 * Check if API server is healthy
 *
 * ENDPOINT: GET /health
 *
 * RETURNS:
 *   - true if server is up
 *   - false if server is down or unhealthy
 *
 * EXAMPLE:
 *   const isHealthy = await checkHealth();
 *   if (!isHealthy) {
 *     alert('Server is down');
 *   }
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get<{ status: string }>('/health');
    return response.data.status === 'healthy';
  } catch (error) {
    return false;
  }
}

// ==========================================================================
// EXPORT API CLIENT (for advanced usage)
// ==========================================================================

/**
 * Export the configured axios instance
 *
 * Use this for custom API calls not covered by the functions above.
 *
 * EXAMPLE:
 *   import { api } from './api';
 *   const response = await api.post('/api/custom-endpoint', data);
 */
export { apiClient as api };
