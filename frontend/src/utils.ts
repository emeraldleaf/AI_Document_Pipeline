/**
 * ============================================================================
 * UTILITY FUNCTIONS - Document Search UI
 * ============================================================================
 *
 * PURPOSE:
 *   Common utility functions used throughout the application.
 *   Keeps code DRY (Don't Repeat Yourself).
 *
 * INCLUDES:
 *   - debounce: Delay function execution
 *   - formatBytes: Human-readable file sizes
 *   - formatDate: Human-readable dates
 *   - truncateText: Shorten long text
 *   - highlightText: Highlight search terms in text
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

// ==========================================================================
// DEBOUNCE
// ==========================================================================

/**
 * Debounce function - delays execution until user stops calling it
 *
 * WHAT IS DEBOUNCING?
 *   Imagine a search box. Every keystroke triggers a search.
 *   User types "invoice" (7 keystrokes = 7 API calls)
 *   That's wasteful! We only care about the final word.
 *
 *   Debouncing waits until user STOPS typing, then executes ONCE.
 *
 * HOW IT WORKS:
 *   1. User types 'i' → Timer starts (300ms)
 *   2. User types 'n' → Timer resets (300ms)
 *   3. User types 'v' → Timer resets (300ms)
 *   ...
 *   4. User stops typing → Timer completes → Execute function
 *
 * BENEFITS:
 *   - Reduces API calls (7 calls → 1 call)
 *   - Saves bandwidth and server load
 *   - Better user experience (fewer loading states)
 *
 * @param func - Function to debounce
 * @param delay - Delay in milliseconds (default: 300)
 * @returns Debounced function
 *
 * EXAMPLE:
 *   const debouncedSearch = debounce((query) => {
 *     console.log('Searching for:', query);
 *   }, 300);
 *
 *   // User types quickly
 *   debouncedSearch('i');    // Timer starts
 *   debouncedSearch('in');   // Timer resets
 *   debouncedSearch('inv');  // Timer resets
 *   // ... 300ms passes ...
 *   // Logs: "Searching for: inv"
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number = 300
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function debounced(...args: Parameters<T>) {
    // Clear previous timer if it exists
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }

    // Start new timer
    timeoutId = setTimeout(() => {
      func(...args);
      timeoutId = null;
    }, delay);
  };
}

// ==========================================================================
// FORMATTING UTILITIES
// ==========================================================================

/**
 * Format bytes to human-readable file size
 *
 * CONVERTS:
 *   1024 → "1.0 KB"
 *   1048576 → "1.0 MB"
 *   1073741824 → "1.0 GB"
 *
 * @param bytes - File size in bytes
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted string
 *
 * EXAMPLE:
 *   formatBytes(1536) → "1.5 KB"
 *   formatBytes(1048576) → "1.0 MB"
 */
export function formatBytes(bytes: number, decimals: number = 1): string {
  if (!bytes || bytes === 0) return '0 Bytes';
  if (isNaN(bytes)) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);

  return `${value.toFixed(decimals)} ${sizes[i]}`;
}

/**
 * Format ISO date string to human-readable format
 *
 * CONVERTS:
 *   "2025-10-31T14:30:00Z" → "Oct 31, 2025"
 *   "2025-10-31T14:30:00Z" → "Oct 31, 2025 2:30 PM" (with time)
 *
 * @param isoString - ISO 8601 date string
 * @param includeTime - Include time in output (default: false)
 * @returns Formatted date string
 *
 * EXAMPLE:
 *   formatDate("2025-10-31T14:30:00Z") → "Oct 31, 2025"
 *   formatDate("2025-10-31T14:30:00Z", true) → "Oct 31, 2025 2:30 PM"
 */
export function formatDate(isoString: string, includeTime: boolean = false): string {
  const date = new Date(isoString);

  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };

  if (includeTime) {
    options.hour = 'numeric';
    options.minute = '2-digit';
    options.hour12 = true;
  }

  return date.toLocaleDateString('en-US', options);
}

/**
 * Format relative time (e.g., "2 hours ago", "3 days ago")
 *
 * CONVERTS:
 *   - Less than 1 minute → "just now"
 *   - Less than 1 hour → "X minutes ago"
 *   - Less than 1 day → "X hours ago"
 *   - Less than 30 days → "X days ago"
 *   - Older → "MMM DD, YYYY"
 *
 * @param isoString - ISO 8601 date string
 * @returns Relative time string
 *
 * EXAMPLE:
 *   formatRelativeTime("2025-10-31T14:00:00Z") → "2 hours ago"
 */
export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;

  return formatDate(isoString);
}

/**
 * Format duration in milliseconds to human-readable string
 *
 * CONVERTS:
 *   150 → "150ms"
 *   1500 → "1.5s"
 *   65000 → "1m 5s"
 *
 * @param ms - Duration in milliseconds
 * @returns Formatted duration string
 *
 * EXAMPLE:
 *   formatDuration(1234) → "1.2s"
 */
export function formatDuration(ms: number): string {
  if (!ms || isNaN(ms)) return '0ms';
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;

  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

// ==========================================================================
// TEXT UTILITIES
// ==========================================================================

/**
 * Truncate text to maximum length with ellipsis
 *
 * EXAMPLE:
 *   truncateText("Hello world this is a long text", 20)
 *   → "Hello world this is..."
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum length
 * @param suffix - Suffix to add (default: "...")
 * @returns Truncated text
 */
export function truncateText(
  text: string,
  maxLength: number,
  suffix: string = '...'
): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Highlight search terms in text
 *
 * EXAMPLE:
 *   highlightText("The quick brown fox", "brown")
 *   → "The quick <mark>brown</mark> fox"
 *
 * @param text - Text to highlight
 * @param query - Search query
 * @param caseSensitive - Case sensitive matching (default: false)
 * @returns HTML string with highlighted terms
 */
export function highlightText(
  text: string,
  query: string,
  caseSensitive: boolean = false,
  searchMode?: string
): string {
  if (!query) return text;

  // Choose highlighting style based on search mode
  let highlightStyle = 'background-color: #fef3c7; color: #92400e;'; // Default yellow for keyword

  if (searchMode === 'semantic') {
    highlightStyle = 'background-color: #dbeafe; color: #1e40af;'; // Blue for semantic
  } else if (searchMode === 'hybrid') {
    highlightStyle = 'background-color: #dcfce7; color: #166534;'; // Green for hybrid
  }

  // Split query into individual words and highlight each one
  const words = query.split(/\s+/).filter(word => word.length > 0);
  let highlightedText = text;

  const flags = caseSensitive ? 'g' : 'gi';

  for (const word of words) {
    if (word.length < 2) continue; // Skip very short words
    const regex = new RegExp(`(${escapeRegex(word)})`, flags);
    highlightedText = highlightedText.replace(regex, `<mark style="${highlightStyle} padding: 2px 4px; border-radius: 3px; font-weight: 600;">$1</mark>`);
  }

  return highlightedText;
}

/**
 * Escape special regex characters in string
 *
 * NEEDED FOR: User input that goes into RegExp
 * Without escaping, special chars like "." or "*" would be treated as regex
 *
 * @param str - String to escape
 * @returns Escaped string
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Extract keywords from text (simple version)
 *
 * REMOVES:
 *   - Common words (the, a, an, is, etc.)
 *   - Short words (less than 3 chars)
 *
 * @param text - Text to extract keywords from
 * @param limit - Maximum keywords to return (default: 10)
 * @returns Array of keywords
 */
export function extractKeywords(text: string, limit: number = 10): string[] {
  const stopWords = new Set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
  ]);

  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ') // Remove punctuation
    .split(/\s+/) // Split on whitespace
    .filter(word => word.length >= 3) // Min 3 chars
    .filter(word => !stopWords.has(word)) // Remove stop words
    .slice(0, limit); // Limit results
}

// ==========================================================================
// VALIDATION UTILITIES
// ==========================================================================

/**
 * Check if string is a valid URL
 *
 * @param str - String to check
 * @returns True if valid URL
 */
export function isValidUrl(str: string): boolean {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if string is empty or only whitespace
 *
 * @param str - String to check
 * @returns True if empty or whitespace
 */
export function isEmpty(str: string | null | undefined): boolean {
  return !str || str.trim().length === 0;
}

// ==========================================================================
// ARRAY UTILITIES
// ==========================================================================

/**
 * Remove duplicate values from array
 *
 * @param arr - Array with potential duplicates
 * @returns Array with unique values
 *
 * EXAMPLE:
 *   unique([1, 2, 2, 3, 3, 3]) → [1, 2, 3]
 */
export function unique<T>(arr: T[]): T[] {
  return Array.from(new Set(arr));
}

/**
 * Chunk array into smaller arrays of specified size
 *
 * @param arr - Array to chunk
 * @param size - Chunk size
 * @returns Array of chunks
 *
 * EXAMPLE:
 *   chunk([1, 2, 3, 4, 5], 2) → [[1, 2], [3, 4], [5]]
 */
export function chunk<T>(arr: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

// ==========================================================================
// CLASS NAME UTILITIES (for conditional CSS classes)
// ==========================================================================

/**
 * Conditionally join CSS class names
 *
 * EXAMPLE:
 *   cn('btn', isActive && 'btn-active', 'btn-primary')
 *   → "btn btn-active btn-primary"
 *
 * @param classes - Class names (string, falsy, or array)
 * @returns Joined class string
 */
export function cn(...classes: (string | boolean | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}
