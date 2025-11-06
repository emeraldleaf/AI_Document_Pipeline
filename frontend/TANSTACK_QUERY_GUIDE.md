# TanStack Query Guide for Junior Developers

**AI Document Pipeline - Frontend**
**Last Updated:** October 2025

---

## Table of Contents

1. [What is TanStack Query?](#what-is-tanstack-query)
2. [Why We Use It](#why-we-use-it)
3. [Installation](#installation)
4. [Core Concepts](#core-concepts)
5. [How We Use It](#how-we-use-it)
6. [Common Patterns](#common-patterns)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)

---

## What is TanStack Query?

**TanStack Query** (formerly React Query) is a powerful data-fetching and state management library for React.

### The Problem It Solves

**WITHOUT TanStack Query:**

```typescript
// ❌ Manual data fetching - lots of boilerplate
function SearchResults() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch('/api/search?q=invoice')
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  return <div>{/* render data */}</div>;
}
```

**Problems:**
- ❌ Lots of repetitive code (loading, error, data state)
- ❌ No caching (same request = multiple API calls)
- ❌ No background updates
- ❌ No retry on failure
- ❌ No deduplication (same request in multiple components = multiple API calls)
- ❌ Manual error handling
- ❌ Hard to keep data fresh

**WITH TanStack Query:**

```typescript
// ✅ Clean, simple, powerful
function SearchResults() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['search', 'invoice'],
    queryFn: () => searchDocuments({ query: 'invoice' }),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  return <div>{/* render data */}</div>;
}
```

**Benefits:**
- ✅ Less code (TanStack Query handles state)
- ✅ Automatic caching (same request uses cache)
- ✅ Background updates (keeps data fresh)
- ✅ Automatic retry on failure
- ✅ Request deduplication (same request = one API call)
- ✅ Built-in error handling
- ✅ Stale-while-revalidate pattern

---

## Why We Use It

### 1. **Caching = Faster App**

When you search for "invoice", TanStack Query caches the results.
If you search again within 5 minutes, it uses the cache (instant results, no API call).

**Real-world example:**
- User searches "invoice"
- Gets results in 300ms (API call)
- User clicks back, searches "invoice" again
- Gets results in <10ms (cached, no API call)

### 2. **Loading & Error States Handled**

No need to write `useState` and `useEffect` for every API call.

```typescript
const { data, isLoading, error } = useQuery({...});

// TanStack Query automatically manages:
// - isLoading: true during first fetch
// - isFetching: true during any fetch (including background)
// - error: contains error if request fails
// - data: contains response data
```

### 3. **Background Updates**

Data stays fresh automatically. TanStack Query refetches data in the background when:
- User focuses the window (returned from another tab)
- Network reconnects
- Component mounts

### 4. **Request Deduplication**

If 3 components request the same data at the same time, TanStack Query makes **ONE** API call and shares the result.

```typescript
// Component A
useQuery({ queryKey: ['stats'], queryFn: getStats });

// Component B (different component, same query)
useQuery({ queryKey: ['stats'], queryFn: getStats });

// Result: Only ONE API call, both components get the data
```

### 5. **Optimistic Updates**

Update UI immediately (before API responds) for better UX.

```typescript
// User clicks "download" button
// UI shows "Downloaded!" immediately
// API call happens in background
// If API fails, TanStack Query rolls back the UI
```

---

## Installation

Already installed in this project!

**Check `package.json`:**
```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.17.19"
  }
}
```

**If starting a new project:**
```bash
npm install @tanstack/react-query
```

**Official docs:** https://tanstack.com/query/latest/docs/framework/react/installation

---

## Core Concepts

### 1. Query Keys

**Query keys** uniquely identify a query and its data in the cache.

```typescript
// Simple key
queryKey: ['stats']

// Key with parameters (different keys = different cache entries)
queryKey: ['search', 'invoice']
queryKey: ['search', 'contract']  // Different cache entry

// Key with multiple parameters
queryKey: ['search', { query: 'invoice', mode: 'hybrid' }]
queryKey: ['search', { query: 'invoice', mode: 'keyword' }]  // Different cache
```

**IMPORTANT:** When parameters change, the query key changes, which triggers a new fetch.

```typescript
// In App.tsx
const [searchQuery, setSearchQuery] = useState('');
const [searchMode, setSearchMode] = useState('hybrid');

const { data } = useQuery({
  // When searchQuery or searchMode changes, this creates a NEW key
  // which triggers a new API call
  queryKey: ['search', searchQuery, searchMode],
  queryFn: () => searchDocuments({ query: searchQuery, mode: searchMode }),
});
```

### 2. Query Functions

**Query functions** fetch the data. They must return a **Promise**.

```typescript
// Simple query function
queryFn: () => fetch('/api/stats').then(res => res.json())

// Query function from our API client
queryFn: () => getStats()

// Query function with parameters
queryFn: ({ queryKey }) => {
  const [_key, query, mode] = queryKey;
  return searchDocuments({ query, mode });
}
```

### 3. Query States

TanStack Query tracks multiple states:

| State | Meaning | When to Use |
|-------|---------|-------------|
| `isLoading` | First fetch in progress | Show spinner on initial load |
| `isFetching` | Any fetch in progress (including background) | Show subtle loading indicator |
| `isError` | Fetch failed | Show error message |
| `isSuccess` | Fetch succeeded | Render data |
| `data` | The fetched data | Access the results |
| `error` | The error object | Show error details |

```typescript
const { data, isLoading, isFetching, isError, error } = useQuery({...});

if (isLoading) return <div>Loading...</div>;  // First load
if (isError) return <div>Error: {error.message}</div>;

return (
  <div>
    {isFetching && <div className="opacity-50">Updating...</div>}
    {/* Show data even if refetching in background */}
    <Results data={data} />
  </div>
);
```

### 4. Stale Time vs Cache Time

**Stale Time:** How long data is considered "fresh"

```typescript
staleTime: 5 * 60 * 1000  // 5 minutes

// Data is "fresh" for 5 minutes
// During this time, TanStack Query won't refetch (uses cache)
// After 5 minutes, data becomes "stale"
// Next time component mounts, TanStack Query refetches
```

**Cache Time:** How long unused data stays in memory

```typescript
cacheTime: 10 * 60 * 1000  // 10 minutes

// After last component using this data unmounts:
// - Data stays in cache for 10 minutes
// - If component re-mounts within 10 min, cache is used
// - After 10 min, cache is garbage collected
```

**Real-world example:**

```typescript
// Search results
staleTime: 5 * 60 * 1000,   // Fresh for 5 min (no refetch)
cacheTime: 30 * 60 * 1000,  // Stay in cache for 30 min

// Timeline:
// 0:00 - User searches "invoice" → API call → Cache stores results
// 0:30 - User searches "invoice" again → Uses cache (fresh)
// 5:00 - User searches "invoice" → Refetches (stale) but shows cache first
// 35:00 - Cache deleted (no activity for 30 min)
```

### 5. Query Client

The **QueryClient** manages all queries and cache.

**Setup in `main.tsx`:**

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,                    // Retry failed requests once
      refetchOnWindowFocus: false, // Don't refetch when user returns to tab
      staleTime: 0,                // Data is stale immediately (default)
    },
  },
});

// Wrap app with provider
<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

---

## How We Use It

### In `App.tsx` - Main Search Component

```typescript
import { useQuery } from '@tanstack/react-query';
import { searchDocuments, getStats } from './api';

function App() {
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [page, setPage] = useState(0);

  // ============================================================
  // QUERY 1: Search Documents
  // ============================================================
  const {
    data: searchResults,
    isLoading: isSearching,
    error: searchError,
    isFetching: isRefetching,
  } = useQuery({
    // Query key includes all parameters
    // When any parameter changes, new API call is made
    queryKey: ['search', debouncedQuery, searchMode, selectedCategory, page],

    // Function to fetch data
    queryFn: () =>
      searchDocuments({
        query: debouncedQuery,
        mode: searchMode,
        category: selectedCategory,
        limit: 20,
        offset: page * 20,
      }),

    // Only run query if we have a search query
    enabled: debouncedQuery.length > 0,

    // Cache search results for 5 minutes
    staleTime: 5 * 60 * 1000,

    // Keep in cache for 30 minutes
    gcTime: 30 * 60 * 1000,  // Note: cacheTime renamed to gcTime in v5
  });

  // ============================================================
  // QUERY 2: System Statistics
  // ============================================================
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,

    // Stats don't change often, cache for 10 minutes
    staleTime: 10 * 60 * 1000,
  });

  // Render UI with loading/error states
  return (
    <div>
      {/* Show stats panel */}
      {stats && <StatsPanel stats={stats} />}

      {/* Show search results */}
      {isSearching && <div>Loading...</div>}
      {searchError && <div>Error: {searchError.message}</div>}
      {searchResults && (
        <div>
          {isFetching && <div className="opacity-50">Updating...</div>}
          {searchResults.results.map(result => (
            <SearchResultCard key={result.id} result={result} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### In `SearchResultCard.tsx` - Lazy Loading Preview

```typescript
import { useQuery } from '@tanstack/react-query';
import { getDocumentPreview } from '../api';

function SearchResultCard({ result }) {
  const [showPreview, setShowPreview] = useState(false);

  // ============================================================
  // Lazy Query: Only fetch when user clicks "Preview"
  // ============================================================
  const {
    data: previewText,
    isLoading: isLoadingPreview,
    error: previewError,
  } = useQuery({
    queryKey: ['preview', result.id],
    queryFn: () => getDocumentPreview(result.id),

    // IMPORTANT: Only fetch when user clicks preview button
    enabled: showPreview,

    // Cache preview for 1 hour (doesn't change)
    staleTime: 60 * 60 * 1000,
  });

  return (
    <div>
      <button onClick={() => setShowPreview(true)}>
        Preview
      </button>

      {showPreview && (
        <div>
          {isLoadingPreview && <div>Loading preview...</div>}
          {previewError && <div>Failed to load preview</div>}
          {previewText && <pre>{previewText}</pre>}
        </div>
      )}
    </div>
  );
}
```

---

## Common Patterns

### Pattern 1: Dependent Queries

Query B depends on data from Query A.

```typescript
// Get document ID first
const { data: document } = useQuery({
  queryKey: ['document', documentId],
  queryFn: () => getDocument(documentId),
});

// Then get related documents (depends on document.category)
const { data: relatedDocs } = useQuery({
  queryKey: ['search', document?.category],
  queryFn: () => searchDocuments({ category: document.category }),

  // Only run when document is loaded
  enabled: !!document,
});
```

### Pattern 2: Pagination

```typescript
const [page, setPage] = useState(0);

const { data } = useQuery({
  queryKey: ['search', query, page],  // Include page in key
  queryFn: () => searchDocuments({
    query,
    offset: page * 20,
    limit: 20
  }),

  // Keep previous data while fetching next page
  // Prevents UI from jumping back to loading state
  placeholderData: (previousData) => previousData,
});

// Navigate pages
<button onClick={() => setPage(p => p - 1)}>Previous</button>
<button onClick={() => setPage(p => p + 1)}>Next</button>
```

### Pattern 3: Infinite Scroll

```typescript
import { useInfiniteQuery } from '@tanstack/react-query';

const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useInfiniteQuery({
  queryKey: ['search', query],
  queryFn: ({ pageParam = 0 }) =>
    searchDocuments({ query, offset: pageParam }),

  getNextPageParam: (lastPage, pages) => {
    // If there are more results, return next offset
    if (lastPage.results.length === 20) {
      return pages.length * 20;
    }
    return undefined;  // No more pages
  },
});

// Render all pages
{data?.pages.map((page, i) => (
  <div key={i}>
    {page.results.map(result => <Result key={result.id} {...result} />)}
  </div>
))}

// Load more button
{hasNextPage && (
  <button onClick={() => fetchNextPage()}>
    {isFetchingNextPage ? 'Loading...' : 'Load More'}
  </button>
)}
```

### Pattern 4: Prefetching

Fetch data before user needs it (better UX).

```typescript
import { useQueryClient } from '@tanstack/react-query';

function SearchResultCard({ result }) {
  const queryClient = useQueryClient();

  // Prefetch preview on hover
  const handleMouseEnter = () => {
    queryClient.prefetchQuery({
      queryKey: ['preview', result.id],
      queryFn: () => getDocumentPreview(result.id),
      staleTime: 60 * 60 * 1000,
    });
  };

  return (
    <div onMouseEnter={handleMouseEnter}>
      {/* When user clicks preview, data is already cached! */}
    </div>
  );
}
```

### Pattern 5: Polling (Auto-Refresh)

Keep data up-to-date by refetching periodically.

```typescript
const { data: stats } = useQuery({
  queryKey: ['stats'],
  queryFn: getStats,

  // Refetch every 30 seconds
  refetchInterval: 30 * 1000,

  // Don't poll when user is not looking at the page
  refetchIntervalInBackground: false,
});
```

---

## Best Practices

### 1. **Use Descriptive Query Keys**

```typescript
// ❌ Bad: Not descriptive
queryKey: ['data']

// ✅ Good: Clear what data this is
queryKey: ['search', query, mode]
```

### 2. **Include All Dependencies in Query Key**

```typescript
// ❌ Bad: Missing searchMode dependency
const { data } = useQuery({
  queryKey: ['search', query],
  queryFn: () => searchDocuments({ query, mode: searchMode }),
});
// If searchMode changes, query won't refetch!

// ✅ Good: All dependencies included
const { data } = useQuery({
  queryKey: ['search', query, searchMode],
  queryFn: () => searchDocuments({ query, mode: searchMode }),
});
```

### 3. **Use `enabled` for Conditional Queries**

```typescript
// ❌ Bad: Query runs even if no query string
const { data } = useQuery({
  queryKey: ['search', query],
  queryFn: () => searchDocuments({ query }),
});

// ✅ Good: Only run when query exists
const { data } = useQuery({
  queryKey: ['search', query],
  queryFn: () => searchDocuments({ query }),
  enabled: query.length > 0,
});
```

### 4. **Set Appropriate Stale Times**

```typescript
// Data that changes frequently (search results)
staleTime: 5 * 60 * 1000  // 5 minutes

// Data that rarely changes (user profile)
staleTime: 60 * 60 * 1000  // 1 hour

// Data that never changes (document preview)
staleTime: Infinity
```

### 5. **Handle Loading and Error States**

```typescript
// ✅ Always handle both states
const { data, isLoading, error } = useQuery({...});

if (isLoading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
return <DataDisplay data={data} />;
```

### 6. **Use TypeScript for Type Safety**

```typescript
import type { SearchResponse } from './types';

const { data } = useQuery<SearchResponse>({
  queryKey: ['search', query],
  queryFn: () => searchDocuments({ query }),
});

// Now 'data' is typed as SearchResponse
// TypeScript will catch errors if you access wrong properties
```

---

## Troubleshooting

### Problem 1: Query Not Refetching

**Symptom:** Data doesn't update when it should

**Causes & Solutions:**

```typescript
// Cause 1: Missing dependency in query key
// ❌ Bad
queryKey: ['search']  // Doesn't include query parameter

// ✅ Fix
queryKey: ['search', query]  // Includes all parameters

// Cause 2: Stale time too long
// ❌ Bad (data cached for 1 hour)
staleTime: 60 * 60 * 1000

// ✅ Fix (reduce stale time)
staleTime: 5 * 60 * 1000

// Cause 3: Query disabled
// ❌ Bad
enabled: false  // Query won't run!

// ✅ Fix
enabled: true
```

### Problem 2: Too Many API Calls

**Symptom:** API being called too frequently

**Causes & Solutions:**

```typescript
// Cause 1: Stale time too short
// ❌ Bad (refetches constantly)
staleTime: 0

// ✅ Fix (cache for reasonable time)
staleTime: 5 * 60 * 1000

// Cause 2: Query key changes too often
// ❌ Bad (creates new query every render)
queryKey: ['search', { query: query }]  // New object every render!

// ✅ Fix (use primitive values)
queryKey: ['search', query]

// Cause 3: No debouncing on search input
// ❌ Bad (API call on every keystroke)
<input onChange={(e) => setQuery(e.target.value)} />

// ✅ Fix (debounce input)
const debouncedQuery = useDebounce(query, 300);
useQuery({ queryKey: ['search', debouncedQuery], ... });
```

### Problem 3: Cached Data Not Updating

**Symptom:** Seeing old data after making changes

**Solution:** Invalidate the query

```typescript
import { useQueryClient } from '@tanstack/react-query';

function EditDocumentButton({ documentId }) {
  const queryClient = useQueryClient();

  const handleEdit = async () => {
    await updateDocument(documentId, changes);

    // Invalidate queries to refetch fresh data
    queryClient.invalidateQueries({ queryKey: ['document', documentId] });
    queryClient.invalidateQueries({ queryKey: ['search'] });
  };
}
```

### Problem 4: Type Errors

**Symptom:** TypeScript errors with query data

**Solution:** Add proper types

```typescript
import type { SearchResponse } from './types';

// ❌ Bad (no types)
const { data } = useQuery({...});
data.results  // TypeScript error: data might be undefined

// ✅ Fix 1: Add type to useQuery
const { data } = useQuery<SearchResponse>({...});

// ✅ Fix 2: Check for undefined
if (data) {
  data.results  // TypeScript happy
}
```

---

## Examples

### Example 1: Simple Query

```typescript
import { useQuery } from '@tanstack/react-query';
import { getStats } from './api';

function StatsDisplay() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 10 * 60 * 1000,  // Cache for 10 minutes
  });

  if (isLoading) return <div>Loading stats...</div>;
  if (error) return <div>Failed to load stats</div>;

  return (
    <div>
      <h2>Total Documents: {data.total_documents}</h2>
      <h3>Categories:</h3>
      <ul>
        {Object.entries(data.categories).map(([name, count]) => (
          <li key={name}>{name}: {count}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Example 2: Search with Parameters

```typescript
import { useQuery } from '@tanstack/react-query';
import { searchDocuments } from './api';

function SearchResults({ query, mode, category }) {
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['search', query, mode, category],
    queryFn: () => searchDocuments({ query, mode, category }),
    enabled: query.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <div>Searching...</div>;
  }

  return (
    <div>
      {isFetching && <div className="text-sm text-gray-500">Updating...</div>}
      {data?.results.length === 0 && <div>No results found</div>}
      {data?.results.map(result => (
        <div key={result.id}>{result.filename}</div>
      ))}
    </div>
  );
}
```

### Example 3: Lazy Query (Fetch on Click)

```typescript
import { useQuery } from '@tanstack/react-query';
import { getDocumentPreview } from './api';

function DocumentCard({ documentId }) {
  const [showPreview, setShowPreview] = useState(false);

  const { data: preview, isLoading } = useQuery({
    queryKey: ['preview', documentId],
    queryFn: () => getDocumentPreview(documentId),
    enabled: showPreview,  // Only fetch when user clicks
  });

  return (
    <div>
      <button onClick={() => setShowPreview(true)}>
        Show Preview
      </button>

      {showPreview && (
        <div>
          {isLoading ? (
            <div>Loading preview...</div>
          ) : (
            <pre>{preview}</pre>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Learn More

**Official Documentation:**
- TanStack Query Docs: https://tanstack.com/query/latest/docs/framework/react/overview
- Installation Guide: https://tanstack.com/query/latest/docs/framework/react/installation
- TypeScript Guide: https://tanstack.com/query/latest/docs/framework/react/typescript

**Our Code Examples:**
- [App.tsx](src/App.tsx) - Main search with useQuery
- [SearchResultCard.tsx](src/components/SearchResultCard.tsx) - Lazy loading preview
- [api.ts](src/api.ts) - API client functions
- [main.tsx](src/main.tsx) - QueryClient setup

**Videos:**
- [TanStack Query in 100 Seconds](https://www.youtube.com/watch?v=novnyCaa7To)
- [React Query Tutorial](https://www.youtube.com/watch?v=lVLz_ASqAio)

---

## Quick Reference

### Common Hooks

```typescript
// Fetch data
useQuery({ queryKey, queryFn, ...options })

// Infinite scroll
useInfiniteQuery({ queryKey, queryFn, getNextPageParam, ...options })

// Access query client
const queryClient = useQueryClient()

// Invalidate (refetch) queries
queryClient.invalidateQueries({ queryKey: ['search'] })

// Prefetch data
queryClient.prefetchQuery({ queryKey, queryFn })
```

### Common Options

```typescript
{
  staleTime: 5 * 60 * 1000,      // 5 minutes
  gcTime: 30 * 60 * 1000,        // 30 minutes (was cacheTime in v4)
  retry: 1,                       // Retry once on failure
  enabled: query.length > 0,      // Conditional fetching
  refetchInterval: 30000,         // Poll every 30s
  refetchOnWindowFocus: false,    // Don't refetch on focus
  placeholderData: prev => prev,  // Keep previous data while fetching
}
```

### Common States

```typescript
const {
  data,              // The fetched data
  isLoading,         // First fetch in progress
  isFetching,        // Any fetch in progress
  isError,           // Fetch failed
  isSuccess,         // Fetch succeeded
  error,             // Error object
  refetch,           // Manual refetch function
} = useQuery({...});
```

---

**Happy querying! 🚀**
