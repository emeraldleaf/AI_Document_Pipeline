# TanStack Query Implementation Summary

**AI Document Pipeline - Frontend**
**Last Updated:** October 2025

---

## What Was Added

Comprehensive TanStack Query (React Query) documentation for junior developers throughout the codebase.

---

## Files Updated

### 1. Main Documentation

**File:** [TANSTACK_QUERY_GUIDE.md](TANSTACK_QUERY_GUIDE.md)

A complete 400+ line guide covering:
- ✅ What is TanStack Query and why use it
- ✅ Core concepts (query keys, query functions, states, caching)
- ✅ Installation instructions
- ✅ How we use it in this project
- ✅ Common patterns (pagination, infinite scroll, prefetching, polling)
- ✅ Best practices
- ✅ Troubleshooting guide
- ✅ Real-world examples
- ✅ Quick reference

**Sections:**
1. What is TanStack Query? (with before/after comparisons)
2. Why We Use It (5 key benefits)
3. Installation (already done)
4. Core Concepts (query keys, functions, states, caching)
5. How We Use It (real examples from our code)
6. Common Patterns (6 patterns with code)
7. Best Practices (6 guidelines)
8. Troubleshooting (4 common problems + solutions)
9. Examples (3 complete working examples)
10. Quick Reference (hooks, options, states)

### 2. App Component

**File:** [src/App.tsx](src/App.tsx)

Added **170+ lines** of detailed TanStack Query documentation:

**Section 1: Introduction (20 lines)**
- What is TanStack Query?
- Why use it?
- Before/after comparison
- Links to official docs and our guide

**Query 1: Search Documents (85 lines)**
- Purpose and how it works
- Query key explanation with examples
- Return values documented
- Caching behavior explained (staleTime, gcTime)
- Conditional fetching explained
- Error handling documented
- Real-world timeline example

**Query 2: System Statistics (45 lines)**
- Purpose and how it works
- Query key explanation
- Polling (auto-refresh) explained
- Caching strategy
- Why shorter stale time
- Example timeline

**Code Comments:**
```typescript
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
 * ... (85 lines total)
 */
```

### 3. SearchResultCard Component

**File:** [src/components/SearchResultCard.tsx](src/components/SearchResultCard.tsx)

Added **110+ lines** of lazy loading documentation:

**Section 1: Lazy Loading Explanation (30 lines)**
- Problem: Loading all previews upfront
- Solution: Load on demand
- How it works (step-by-step)
- Benefits (4 key advantages)

**Query: Document Preview (80 lines)**
- Purpose (lazy loading pattern)
- Query key explanation
- Enabled option (key to lazy loading)
- Caching strategy
- States documentation
- Example timeline
- Before/after comparison

**Updated Features:**
- ✅ TanStack Query for preview fetching
- ✅ Proper loading state handling
- ✅ Proper error state handling
- ✅ Success state with data

**Code Comments:**
```typescript
/**
 * Lazy Query: Document Preview
 *
 * PURPOSE:
 *   Fetch document preview text only when user clicks "Preview" button.
 *
 * ENABLED:
 *   enabled: showPreview
 *
 *   - Query ONLY runs when showPreview is true
 *   - User clicks "Preview" → showPreview = true → query runs
 *   - This is LAZY LOADING (fetch on demand, not upfront)
 *
 * ... (80 lines total)
 */
```

---

## Key Concepts Explained

### 1. Caching

**Explained in:**
- TANSTACK_QUERY_GUIDE.md (Core Concepts section)
- App.tsx (both queries)
- SearchResultCard.tsx (lazy loading)

**Key points:**
- `staleTime` = how long data is fresh
- `gcTime` = how long cache persists after unmount
- Search results: 5 min cache
- Stats: 30 sec cache (changes more frequently)
- Previews: 1 hour cache (static content)

### 2. Query Keys

**Explained in:**
- TANSTACK_QUERY_GUIDE.md (Core Concepts section)
- App.tsx (with examples)

**Key points:**
- Uniquely identify queries and cache
- Include all dependencies
- Different keys = different cache entries
- Examples:
  ```typescript
  ['search', 'invoice', 'hybrid', undefined, 0]
  ['search', 'invoice', 'keyword', undefined, 0]  // Different mode = different key
  ```

### 3. Lazy Loading

**Explained in:**
- TANSTACK_QUERY_GUIDE.md (Common Patterns section)
- SearchResultCard.tsx (detailed explanation)

**Key points:**
- Use `enabled` option to control when query runs
- Only fetch data when user needs it
- Benefits: faster load, less bandwidth, better performance
- Example: Preview only loaded when user clicks button

### 4. Polling (Auto-Refresh)

**Explained in:**
- TANSTACK_QUERY_GUIDE.md (Common Patterns section)
- App.tsx (stats query)

**Key points:**
- Use `refetchInterval` to auto-refresh data
- Stats refresh every 60 seconds
- Keeps dashboard current without user action
- User sees new documents appear automatically

### 5. Conditional Fetching

**Explained in:**
- TANSTACK_QUERY_GUIDE.md (Best Practices section)
- App.tsx (search query)
- SearchResultCard.tsx (preview query)

**Key points:**
- Use `enabled` to control when query runs
- Search: only if query string exists
- Preview: only if user wants to see it
- Prevents unnecessary API calls

---

## Before vs After Comparison

### Without TanStack Query (Manual Approach)

```typescript
// ❌ Manual data fetching - lots of code
function SearchResults() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch('/api/search?q=invoice')
      .then(res => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
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
- 25+ lines of boilerplate
- No caching (same request = multiple API calls)
- No retry on failure
- Manual state management
- Hard to keep data fresh

### With TanStack Query (Our Approach)

```typescript
// ✅ TanStack Query - clean and powerful
function SearchResults() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['search', 'invoice'],
    queryFn: () => searchDocuments({ query: 'invoice' }),
    staleTime: 5 * 60 * 1000,  // Cache 5 min
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  return <div>{/* render data */}</div>;
}
```

**Benefits:**
- 8 lines of code (65% less code)
- Automatic caching
- Automatic retry
- Automatic state management
- Background updates

---

## Performance Benefits

### Search Query Performance

**Without Caching:**
```
User searches "invoice" → API call (300ms)
User searches "invoice" again → API call (300ms)
User searches "invoice" again → API call (300ms)
Total: 900ms
```

**With TanStack Query Caching:**
```
User searches "invoice" → API call (300ms) → Cached
User searches "invoice" again → Cache hit (<10ms)
User searches "invoice" again → Cache hit (<10ms)
Total: ~320ms (64% faster!)
```

### Preview Performance

**Without Lazy Loading:**
```
Page loads with 20 results
→ 20 preview API calls immediately
→ Slow page load
→ Wasted bandwidth (user might not view all)
```

**With Lazy Loading (TanStack Query):**
```
Page loads with 20 results
→ 0 preview API calls initially
→ Fast page load
User clicks "Preview" on result #5
→ 1 API call (only for clicked result)
→ Cached for future opens
```

### Stats Auto-Refresh

**Without Polling:**
```
Stats shown on page load
User sees outdated stats
Must manually refresh page to see updates
```

**With TanStack Query Polling:**
```
Stats shown on page load
Auto-refresh every 60 seconds
User always sees current stats
No manual refresh needed
```

---

## Real-World Usage Examples

### Example 1: Search with Caching

```typescript
// User behavior timeline:
0:00 - User searches "invoice"
     → Query: ['search', 'invoice', 'hybrid', undefined, 0]
     → API call (300ms)
     → Results cached

0:30 - User switches to "keyword" mode
     → Query: ['search', 'invoice', 'keyword', undefined, 0]  (NEW key)
     → API call (300ms)
     → Results cached

1:00 - User switches back to "hybrid" mode
     → Query: ['search', 'invoice', 'hybrid', undefined, 0]  (EXISTING key)
     → Cache hit (<10ms) - INSTANT!
     → No API call

5:30 - Cache expires (5 min staleTime)
     - User switches to "hybrid" again
     → Query refetches (background)
     → Shows cached data first (UX++)
     → Updates with fresh data when ready
```

### Example 2: Lazy Loading Preview

```typescript
// User behavior timeline:
0:00 - Page loads with 20 search results
     → 0 preview API calls (lazy loading)

0:05 - User clicks "Preview" on result #1
     → showPreview = true
     → enabled: showPreview triggers query
     → API call for preview (200ms)
     → Preview cached

0:10 - User closes preview
     → Preview still in cache

0:15 - User reopens preview
     → Cache hit (<10ms) - INSTANT!
     → No API call

0:20 - User clicks "Preview" on result #2
     → Different queryKey: ['preview', 'result-2-id']
     → API call (200ms)
     → Cached separately
```

### Example 3: Stats Auto-Refresh

```typescript
// Timeline:
0:00 - User opens page
     → Stats query: ['stats']
     → API call
     → Shows: 1,000 documents

1:00 - Auto-refresh (refetchInterval: 60s)
     → Background API call
     → Updates: 1,002 documents (2 new docs processed)

2:00 - Auto-refresh
     → Updates: 1,005 documents

// User sees stats update automatically
// No manual refresh needed
```

---

## What Junior Developers Will Learn

From this documentation, junior developers will understand:

### 1. Data Fetching Best Practices
- ✅ Caching strategies
- ✅ Error handling
- ✅ Loading states
- ✅ Retry logic

### 2. Performance Optimization
- ✅ Lazy loading (fetch on demand)
- ✅ Request deduplication
- ✅ Background updates
- ✅ Stale-while-revalidate pattern

### 3. TanStack Query Patterns
- ✅ Simple queries
- ✅ Queries with parameters
- ✅ Conditional queries (enabled)
- ✅ Polling (refetchInterval)
- ✅ Lazy queries

### 4. React Best Practices
- ✅ Separation of concerns
- ✅ Declarative programming
- ✅ State management
- ✅ Performance optimization

---

## Quick Reference

### Documentation Files

| File | Lines | Purpose |
|------|-------|---------|
| `TANSTACK_QUERY_GUIDE.md` | 400+ | Complete beginner guide |
| `App.tsx` (comments) | 170+ | Search & stats queries |
| `SearchResultCard.tsx` (comments) | 110+ | Lazy loading pattern |
| **Total** | **680+** | **Comprehensive docs** |

### Query Patterns Used

| Pattern | File | Description |
|---------|------|-------------|
| Simple Query | App.tsx (stats) | Basic data fetching |
| Parameterized Query | App.tsx (search) | Query with multiple params |
| Lazy Query | SearchResultCard.tsx | Fetch on user action |
| Polling | App.tsx (stats) | Auto-refresh data |
| Conditional Query | Both files | Control when query runs |

### Cache Strategies

| Data Type | Stale Time | Reason |
|-----------|------------|--------|
| Search Results | 5 minutes | Balance between freshness and performance |
| Stats | 30 seconds | Changes frequently (new docs) |
| Previews | 1 hour | Static content, doesn't change |

---

## Links and Resources

**Our Documentation:**
- [Complete Guide](TANSTACK_QUERY_GUIDE.md) - Full TanStack Query guide
- [App.tsx](src/App.tsx) - See search & stats queries
- [SearchResultCard.tsx](src/components/SearchResultCard.tsx) - See lazy loading

**Official Documentation:**
- [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview)
- [Installation Guide](https://tanstack.com/query/latest/docs/framework/react/installation)
- [TypeScript Guide](https://tanstack.com/query/latest/docs/framework/react/typescript)

**Learning Resources:**
- [React Query in 100 Seconds](https://www.youtube.com/watch?v=novnyCaa7To)
- [React Query Tutorial](https://www.youtube.com/watch?v=lVLz_ASqAio)

---

## Summary

✅ **680+ lines** of comprehensive TanStack Query documentation added
✅ **3 files** updated with detailed comments
✅ **5 query patterns** explained with examples
✅ **Real-world timelines** showing how caching works
✅ **Before/after comparisons** showing benefits
✅ **Performance improvements** quantified
✅ **Best practices** documented
✅ **Troubleshooting guide** included

Junior developers can now:
- Understand what TanStack Query is and why we use it
- Learn from real working examples in our code
- Apply best practices in their own code
- Troubleshoot common issues
- Reference the guide for patterns and solutions

**All TanStack Query usage is fully documented and junior-developer friendly! 🎓**
