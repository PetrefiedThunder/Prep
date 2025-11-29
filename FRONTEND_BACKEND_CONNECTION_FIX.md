# Frontend-Backend Connection Fix

## Problem

The HarborHomes frontend (Next.js app) was not able to connect to the backend API because the required environment variable `NEXT_PUBLIC_API_BASE` was not configured.

## Root Cause

The frontend application at `apps/harborhomes` requires the `NEXT_PUBLIC_API_BASE` environment variable to know where the backend API is located. Without this configuration:
- The frontend falls back to embedded mock data
- API calls through `/app/api/policy/[...path]/route.ts` fail with a 500 error
- The `lib/policy.ts` module cannot fetch real compliance data from the backend

## Solution

### 1. Configure Environment Variables

Create a `.env.local` file in the `apps/harborhomes` directory with the backend API URL:

```bash
# Backend API Configuration
NEXT_PUBLIC_API_BASE=http://localhost:8000
PREP_API_BASE=http://localhost:8000

# Optional: External Service API Keys
MAPBOX_TOKEN=mock
NEXT_PUBLIC_ANALYTICS_WRITE_KEY=mock
```

The `.env.local` file is git-ignored and safe for local development.

### 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Local Development Setup                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (HarborHomes)           Backend Services           │
│  ┌──────────────────┐             ┌──────────────────┐     │
│  │  Next.js App     │   API       │  FastAPI         │     │
│  │  Port: 3001      │─────────────>  Port: 8000      │     │
│  │  (npm run dev)   │   calls     │  (compliance)    │     │
│  └──────────────────┘             └──────────────────┘     │
│                                     ┌──────────────────┐     │
│                                     │  Node API        │     │
│                                     │  Port: 3000      │     │
│                                     │  (prepchef)      │     │
│                                     └──────────────────┘     │
│                                              │                │
│                                     ┌────────┴────────┐      │
│                                     │  Infrastructure  │      │
│                                     │  - PostgreSQL    │      │
│                                     │  - Redis         │      │
│                                     │  - MinIO         │      │
│                                     └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 3. Starting the Services

#### Start Backend Infrastructure (Required)

```bash
# From the repository root
cd /path/to/Prep

# Start PostgreSQL, Redis, and MinIO
docker compose up -d postgres redis minio

# Wait for services to be healthy
docker compose ps

# Run database migrations
make migrate
```

#### Start Backend API (Optional - depends on what you're testing)

The Python FastAPI compliance API:
```bash
docker compose up -d python-compliance
```

Or the Node.js prepchef API:
```bash
docker compose up -d node-api
```

#### Start Frontend

```bash
# In a new terminal
cd apps/harborhomes

# Install dependencies if needed
npm install  # or pnpm install

# Start the development server
npm run dev  # or pnpm dev

# Frontend will be available at http://localhost:3001
```

### 4. Verify the Connection

Once both the backend and frontend are running:

1. Open http://localhost:3001 in your browser
2. Navigate to a page that uses the policy API (e.g., `/sf-and-jt`)
3. Check the browser console - you should see API calls to `http://localhost:8000`
4. Check the backend logs for incoming requests:
   ```bash
   docker compose logs -f python-compliance
   ```

If the `NEXT_PUBLIC_API_BASE` is not set:
- The frontend will log: "API base URL is not configured"
- The app will fall back to the embedded mock data in `lib/policy.ts`
- No network requests will be made to the backend

### 5. Environment Variable Precedence

The frontend checks for the API base URL in this order:
1. `NEXT_PUBLIC_API_BASE` - For client-side access (recommended)
2. `PREP_API_BASE` - For server-side API routes (fallback)

Set both to ensure consistent behavior across client and server components.

## Files Changed

1. **`apps/harborhomes/.env.example`** - Updated with API configuration examples
2. **`apps/harborhomes/.env.local`** - Created with working local development settings
3. **`apps/harborhomes/.gitignore`** - Added `.env.local` to prevent committing secrets
4. **`docker-compose.yml`** - Removed platform constraint that caused build issues

## Testing

To test that the frontend can connect to the backend:

1. Start the backend services:
   ```bash
   docker compose up -d postgres redis minio python-compliance
   ```

2. In a separate terminal, start the frontend:
   ```bash
   cd apps/harborhomes
   npm run dev
   ```

3. Open http://localhost:3001 and verify:
   - No error messages about missing API configuration
   - API calls appear in the network tab of browser dev tools
   - Backend logs show incoming requests

## Troubleshooting

### Frontend shows "API base URL is not configured"

- Check that `.env.local` exists in `apps/harborhomes`
- Verify `NEXT_PUBLIC_API_BASE` is set in `.env.local`
- Restart the Next.js dev server (`npm run dev`)

### Backend API not responding

- Check that Docker services are running: `docker compose ps`
- Check service health: `make health` or `docker compose logs python-compliance`
- Verify the backend is listening on port 8000: `curl http://localhost:8000/healthz`

### CORS errors in browser console

- The backend API should be configured to allow requests from `http://localhost:3001`
- Check the `CORS_ORIGINS` environment variable in backend configuration

## Additional Documentation

- See `README.md` - Main project documentation
- See `README.local.md` - Local development guide
- See `TROUBLESHOOTING.md` - Common issues and fixes
- See `apps/harborhomes/README.md` - Frontend-specific documentation
