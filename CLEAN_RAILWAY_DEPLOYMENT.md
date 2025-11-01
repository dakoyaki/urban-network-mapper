# Clean Railway Deployment Guide

This guide will help you set up a clean, working deployment on Railway.

## 🔴 Current Issues

You have:
- ✅ Backend working (urban-mapper-backend)
- ⚠️ Frontend with build issues
- ⚠️ Multiple duplicate database services

## 🧹 Step 1: Clean Up Railway Services

### In Railway Dashboard:

1. **Go to**: https://railway.app/dashboard
2. **Select**: urban-network-mapper project
3. **Delete these services**:
   - ❌ Postgres
   - ❌ Postgres-KdyN  
   - ❌ urban-mapper-db
   - ❌ urban-mapper-frontend

**Keep only**: urban-mapper-backend

## 🆕 Step 2: Add Fresh Database

### In Railway Dashboard:

1. Click **"+"** (Add Service)
2. Select **"Database"**
3. Select **"PostgreSQL"**
4. Railway creates it automatically with PostGIS enabled

**Note the DATABASE_URL** - Railway auto-generates it

## ⚙️ Step 3: Configure Backend

### In Railway Dashboard → Backend Service:

1. **Go to**: urban-mapper-backend → Settings
2. **Variables tab**, add/verify:

```bash
DATABASE_URL=<Railway auto-generates this when you connect database>
SECRET_KEY=<generate using: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
CORS_ORIGINS=*
DEFAULT_PROJECT_EPSG=3857
```

3. **Settings tab**, verify:
   - Root Directory: `backend`
   - Build Command: Leave empty (Docker handles it)
   - Start Command: `gunicorn -c gunicorn.conf.py wsgi:app`

4. **Click "Redeploy"** to apply changes

## 🌐 Step 4: Deploy Frontend Correctly

### Option A: Via Dashboard (Recommended)

1. Click **"+"** (Add Service)
2. Select **"GitHub Repo"**
3. Select: `dakoyaki/urban-network-mapper`
4. Service appears in dashboard

5. **Click on the service**
6. **Settings tab**:
   - Root Directory: `frontend`
   - Build Command: Leave empty (Docker handles it)
   - Start Command: Leave empty (nginx serves static files)
   
7. **Variables tab**, add:
   ```
   VITE_API_BASE_URL=https://urban-mapper-backend-production.up.railway.app/api
   ```

8. **Wait for deployment** (~3-5 minutes)

### Option B: Via CLI (Alternative)

If dashboard doesn't work, try CLI:

```bash
cd /Users/macos/Desktop/urban_mapper/frontend
railway up --detach
```

**Then** configure Variables in dashboard

## 🔗 Step 5: Update CORS

Once frontend has a URL:

1. Go to **backend service** → Variables
2. Update `CORS_ORIGINS`:
   ```
   https://your-frontend-url.up.railway.app
   ```
3. Backend auto-redeploys

## ✅ Step 6: Verify Everything

### Test Backend:
```bash
curl https://urban-mapper-backend-production.up.railway.app/api/projects
```

Should return:
```json
{"current_page":1,"pages":1,"projects":[],"total":0}
```

### Test Frontend:
1. Open your frontend URL in browser
2. Check console (F12) - should see no CORS errors
3. Map should load
4. Try drawing a line

### Test Database:
1. Draw a line on map
2. Refresh page
3. Line should persist

### Test Export:
1. Draw some lines
2. Click "Export GeoPackage"
3. Download should work
4. Open in QGIS - data should appear

## 🐛 Troubleshooting

### Frontend Build Fails

**Check**: Railway logs
**Common issues**:
- Missing VITE_API_BASE_URL → Add variable
- npm install fails → Check package.json
- Docker build fails → Check Dockerfile

**Fix**: Check logs for specific error

### Backend Can't Connect to Database

**Check**: `DATABASE_URL` in backend variables
**Fix**: Ensure database service is connected via dashboard

### CORS Errors

**Check**: Frontend and backend URLs
**Fix**: Update `CORS_ORIGINS` in backend to match frontend URL exactly

### Data Not Saving

**Check**: Database service is active
**Fix**: Verify PostGIS extensions are enabled

## 📋 Final Checklist

After deployment:

- [ ] Only 3 services: backend, frontend, 1 database
- [ ] Backend returns 200 at /api/projects
- [ ] Frontend loads with no console errors
- [ ] Can draw and save lines
- [ ] Export works
- [ ] No CORS errors
- [ ] All environment variables set

## 🎉 You're Done!

Your Urban Network Mapper is live and ready for students!

Share the frontend URL with your class to start mapping.

