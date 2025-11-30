# CORS Fix for Production

## Issue
Frontend at `https://hamza123545.github.io/physical-ai-book/` cannot access backend due to CORS policy.

## Solution

### Option 1: Update Render Environment Variables (Recommended)

1. Go to Render Dashboard
2. Select your backend service: `physical-ai-backend`
3. Go to **Environment** tab
4. Add/Update `CORS_ORIGINS`:
   ```
   https://hamza123545.github.io,https://hamza123545.github.io/physical-ai-book
   ```
5. Save and redeploy

### Option 2: Code Already Updated

The backend code has been updated to include the frontend URL as default. After pushing to GitHub and Render redeploys, it should work.

## Verify

After deployment, test:
```bash
curl -X OPTIONS https://physical-ai-backend-9lxv.onrender.com/api/chat \
  -H "Origin: https://hamza123545.github.io" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

Should return `Access-Control-Allow-Origin: https://hamza123545.github.io`

