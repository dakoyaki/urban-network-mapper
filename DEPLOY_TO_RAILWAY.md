# Complete Railway Deployment Guide

**Time**: 10 minutes  
**Difficulty**: Easy  
**Result**: Fully working Urban Network Mapper

## Step 1: Create New Project in Railway Dashboard

1. Go to: https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose: `dakoyaki/urban-network-mapper`
5. Wait for Railway to detect the repo

## Step 2: Railway Auto-Creates Services

Railway should automatically detect and create:
- `urban-mapper-backend` (from backend/Dockerfile)
- (Possibly) frontend service

**If auto-creation doesn't work**, we'll add services manually (Step 4)

## Step 3: Add PostgreSQL Database

**IMPORTANT**: Do this FIRST before configuring backend

1. In your Railway project, click **"+"** button
2. Select **"Database"**
3. Select **"PostgreSQL"**
4. Railway creates it automatically with PostGIS enabled
5. **Note**: Railway auto-generates DATABASE_URL

## Step 4: Configure Backend Service

### A. Find Backend Service

If Railway auto-created it, it's named `urban-mapper-backend`

If not:
1. Click **"+"** → **"GitHub Repo"**
2. Select: `dakoyaki/urban-network-mapper`
3. Railway detects and creates service

### B. Settings Configuration

Click on backend service → **Settings**:

- **Root Directory**: `backend`
- **Build Command**: Leave empty
- **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:app`

### C. Environment Variables

Click on backend service → **Variables** → **Add**:

```
Variable: DATABASE_URL
Value: (Railway auto-generates when you connect database - just reference it)

Variable: SECRET_KEY  
Value: [GENERATE THIS - I'll provide command below]

Variable: FLASK_ENV
Value: production

Variable: CORS_ORIGINS
Value: *

Variable: DEFAULT_PROJECT_EPSG
Value: 3857
```

**Generate SECRET_KEY**:
Run in your terminal:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste as SECRET_KEY value.

### D. Verify DATABASE_URL

1. Go to your PostgreSQL service
2. Click **Variables** tab  
3. Find `DATABASE_URL` or `POSTGRES_URL`
4. Copy this value
5. Go to backend service → Variables
6. If DATABASE_URL isn't there, add it manually
7. Paste the database URL

**Important**: Change `postgresql://` to `postgresql+psycopg2://` in the URL

Example:
```
postgresql+psycopg2://postgres:PASSWORD@HOST:PORT/railway
```

### E. Deploy Backend

Backend should auto-deploy after saving variables.  
Wait for status to show "Active" ✅

**Test**: 
```
curl https://your-backend-url.up.railway.app/api/projects
```

Should return JSON.

## Step 5: Deploy Frontend Service

### A. Create Frontend Service

1. Click **"+"** → **"GitHub Repo"**
2. Select: `dakoyaki/urban-network-mapper` (same repo)

Railway creates a SECOND service pointing to same repo

### B. Settings Configuration

Click on frontend service → **Settings**:

- **Root Directory**: `frontend`
- **Build Command**: Leave empty  
- **Start Command**: Leave empty

### C. Environment Variables

Click on frontend service → **Variables** → **Add**:

```
Variable: VITE_API_BASE_URL
Value: https://urban-mapper-backend-production.up.railway.app/api

Variable: VITE_VWORLD_API_KEY
Value: [Your V-World API key, or leave empty if not using Korean maps]
```

**⚠️ CRITICAL**: 
- Replace `urban-mapper-backend-production` with YOUR actual backend URL
- Must use HTTPS
- Must include `/api` at the end

### D. Deploy Frontend

Wait for status to show "Active" ✅

### E. Get Frontend URL

Click on frontend service → **Networking** tab  
Copy the URL (e.g., `urban-mapper-frontend-production.up.railway.app`)

## Step 6: Update CORS

Now that you have frontend URL:

1. Go to backend service → Variables
2. Find `CORS_ORIGINS`  
3. Change from `*` to: `https://your-frontend-url.up.railway.app`
4. Backend auto-redeploys

## Step 7: Verify Everything Works

### Test Backend
```bash
curl https://your-backend-url.up.railway.app/api/projects
```

### Test Frontend
1. Open: `https://your-frontend-url.up.railway.app`
2. Map should load
3. Check browser console (F12) - should see NO CORS errors
4. Try drawing a sidewalk line
5. Refresh page - line should persist

### Test Export
1. Draw some lines
2. Click "Export GeoPackage"
3. File should download
4. Open in QGIS - data should appear

## Final Checklist

Your deployment is complete when:

- [ ] 3 services: backend, frontend, 1 PostgreSQL
- [ ] Backend returns 200 at /api/projects
- [ ] Frontend loads without errors
- [ ] Can draw and save lines
- [ ] No CORS errors in browser console
- [ ] Export works

## Your URLs

After deployment, you'll have:
- Backend: `https://urban-mapper-backend-production.up.railway.app`
- Frontend: `https://urban-mapper-frontend-production.up.railway.app`

Share the frontend URL with your students! 🎉

## Troubleshooting

If something doesn't work:
1. Check logs in Railway dashboard
2. Verify all environment variables are set
3. Check database is "Active"
4. See TROUBLESHOOTING_RAILWAY.md for details
