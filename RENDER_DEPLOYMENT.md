# Render Deployment Guide

## Quick Setup

1. **Push to GitHub** - Backend folder ko alag repository mein push kiya hai

2. **Create Web Service on Render:**
   - Go to Render Dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository (backend repository: `api.physical_book`)
   - Configure:
     - **Name**: `physical-ai-backend`
     - **Root Directory**: `.` (LEAVE EMPTY - root directory, koi subfolder nahi)
     - **Environment**: `Docker`
     - **Dockerfile Path**: `Dockerfile` (root mein hai, exactly `Dockerfile` likho)
     
   **⚠️ IMPORTANT:**
   - Root Directory ko **COMPLETELY EMPTY** rakho (`.` mat likho, bilkul khali chhodo)
   - Dockerfile Path mein sirf `Dockerfile` likho (no `./` or path)

3. **Set Environment Variables:**
   ```
   DATABASE_URL=postgresql://...
   QDRANT_URL=https://...
   QDRANT_API_KEY=...
   OPENAI_API_KEY=sk-...
   JWT_SECRET_KEY=your-secret-key
   BETTER_AUTH_SECRET=your-better-auth-secret
   BETTER_AUTH_URL=https://your-backend.onrender.com
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-frontend-url.com
   ```

4. **Deploy** - Render will automatically build and deploy using Dockerfile

## Docker Commands (Local Testing)

```bash
# Build image
docker build -t physical-ai-backend .

# Run locally
docker run -p 8000:8000 --env-file .env physical-ai-backend

# Or with docker-compose
docker-compose up
```

## Render Configuration

- **Build Command**: (Not needed - Docker handles it)
- **Start Command**: (Not needed - Dockerfile CMD handles it)
- **Root Directory**: `.` (root directory - koi subfolder nahi)
- **Dockerfile Path**: `Dockerfile` (root mein hai)

