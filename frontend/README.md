# Document Search UI - Frontend

Modern, high-performance React application for searching and managing documents.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000 in your browser.

## Features

- ⚡ **Fast Search** - Real-time results with <300ms latency
- 🔍 **Multiple Modes** - Keyword, semantic, and hybrid search
- 📄 **Document Preview** - View document content inline
- ⬇️ **Download** - Download original files
- 📊 **Statistics** - View collection overview
- 📱 **Responsive** - Works on mobile, tablet, desktop

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **TanStack Query** - Data fetching & caching
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **Axios** - HTTP client

## Available Scripts

```bash
# Development server
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint

# Production build
npm run build

# Preview production build
npm run preview
```

## Configuration

Create `.env.local` file:

```bash
# API backend URL
VITE_API_URL=http://localhost:8000
```

See `.env.example` for all available options.

## Project Structure

```
src/
├── components/          # React components
│   ├── SearchResultCard.tsx
│   ├── SearchFilters.tsx
│   └── StatsPanel.tsx
├── App.tsx             # Main app component
├── main.tsx            # Entry point
├── types.ts            # TypeScript types
├── api.ts              # API client
├── utils.ts            # Utility functions
└── index.css           # Global styles
```

## API Integration

The frontend communicates with the FastAPI backend:

- **Search:** `GET /api/search`
- **Document Details:** `GET /api/documents/{id}`
- **Preview:** `GET /api/preview/{id}`
- **Download:** `GET /api/download/{id}`
- **Statistics:** `GET /api/stats`

All API calls are type-safe and cached by React Query.

## Development

**With Backend:**

1. Start backend: `cd ../api && uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Open http://localhost:3000

**Vite Proxy:**

In development, requests to `/api/*` are proxied to the backend (configured in `vite.config.ts`).

## Building for Production

```bash
# Build optimized bundle
npm run build

# Output in dist/ directory
# Deploy dist/ to:
# - Vercel: vercel deploy
# - Netlify: netlify deploy
# - AWS S3: aws s3 sync dist/ s3://your-bucket/
# - Any static host
```

## Performance Optimizations

- ✅ **Code splitting** - Vendor chunks separated
- ✅ **React Query caching** - 5-minute cache for search results
- ✅ **Debounced search** - 300ms delay to reduce API calls
- ✅ **Lazy loading** - Components load on demand
- ✅ **Tree shaking** - Unused code removed
- ✅ **Minification** - Production bundle minified

## Troubleshooting

**Problem:** API requests fail with CORS error

**Solution:** Backend must have CORS middleware configured:

```python
# In api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

**Problem:** Module not found errors

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
```

---

**Problem:** Build errors

**Solution:** Check TypeScript errors:
```bash
npm run typecheck
```

## Documentation

- [Full Deployment Guide](../SEARCH_UI_DEPLOYMENT.md)
- [API Documentation](http://localhost:8000/docs)
- [React Query Docs](https://tanstack.com/query/latest)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Vite Docs](https://vitejs.dev/)

## License

MIT
