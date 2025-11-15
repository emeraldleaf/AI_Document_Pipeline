# API Gateway Service (Not Yet Implemented)

## Status: 🔜 Future Enhancement

This service is **designed but not yet implemented**. It's part of the optional enhancement roadmap.

---

## Purpose

Provide a unified entry point for all API requests with:
- **Authentication & Authorization** - JWT tokens, API keys
- **Rate Limiting** - Prevent abuse
- **Request Routing** - Route to appropriate services
- **Load Balancing** - Distribute traffic
- **CORS Handling** - Cross-origin requests

---

## Planned Technology

- **Nginx** or **Kong** API Gateway
- JWT authentication
- Rate limiting per client
- SSL/TLS termination

---

## When to Implement

Implement this service when:
- You need authentication/authorization
- You have multiple frontend clients
- You need rate limiting
- You're deploying to production

---

## Current Workaround

For now, frontend connects directly to services:
- Ingestion Service: `http://localhost:8000`
- Notification Service: `http://localhost:8001`

This works fine for development and small deployments.

---

## Implementation Guide

See [EVENT_DRIVEN_ARCHITECTURE.md](../../EVENT_DRIVEN_ARCHITECTURE.md) for:
- Complete design specification
- Nginx configuration examples
- Authentication patterns
- Deployment instructions

---

## Quick Implementation (When Needed)

1. Create `nginx.conf` with routing rules
2. Add JWT verification
3. Configure rate limiting
4. Create Dockerfile
5. Add to docker-compose

**Estimated time:** 1-2 days

---

**Status:** Optional - System works without this
**Priority:** Low (implement when needed for production)
**Documentation:** Complete design available in architecture docs
