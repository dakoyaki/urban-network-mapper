# Deployment Guide for Walkability Network Builder

This guide provides step-by-step instructions for deploying the Urban Mapper application to production.

## ⚠️ Important: PostGIS Requirements

This application **requires PostgreSQL with PostGIS and SFCGAL extensions**. Standard managed PostgreSQL services often don't include these extensions by default. Choose one of the following deployment strategies:

### Option 1: Render.com (Recommended for Simplicity)

**Render does NOT support PostGIS by default**, but we can work around this:

1. **Deploy a custom PostGIS database container** OR
2. **Use a managed PostGIS service** (see alternative options below)

#### Strategy A: Custom PostGIS Database on Render

Since Render's built-in PostgreSQL doesn't support PostGIS, you'll need to:

1. **Create a Web Service** that runs the PostGIS database
2. **Create another Web Service** for the Flask backend
3. **Create a static site** for the frontend

**Steps:**

1. **Create a PostGIS Database Service:**
   ```yaml
   # Create render-db.yaml
   services:
     - type: web
       name: urban-mapper-db
       plan: starter
       runtime: docker
       dockerfilePath: ./database/Dockerfile
       envVars:
         - key: POSTGRES_USER
           value: walknet
         - key: POSTGRES_PASSWORD
           generateValue: true
         - key: POSTGRES_DB
           value: walknet
   ```

2. **Create Database Dockerfile:**
   ```dockerfile
   # database/Dockerfile
   FROM postgis/postgis:16-3.4
   EXPOSE 5432
   ```

3. **Deploy Backend Service** (see `render.yaml`)

4. **Deploy Frontend Service** (see `render-frontend.yaml`)

### Option 2: Railway.app (Easier PostGIS Setup)

Railway supports PostGIS more easily:

1. **Create account** at [railway.app](https://railway.app)
2. **Create new project**
3. **Add PostgreSQL** (includes PostGIS)
4. **Deploy from GitHub**

See Railway-specific instructions below.

### Option 3: DigitalOcean App Platform with Managed Postgres + PostGIS

DigitalOcean offers managed databases with PostGIS.

### Option 4: AWS / Google Cloud / Azure

Full cloud platforms with managed PostGIS options:
- **AWS RDS PostgreSQL with PostGIS**
- **Google Cloud SQL for PostgreSQL with PostGIS**
- **Azure Database for PostgreSQL with PostGIS**

---

## Render.com Full Deployment Guide

### Prerequisites

1. GitHub account with this repository
2. Render account (free tier available)
3. V-World API key (for Korean basemaps)

### Step 1: Prepare Repository

Make sure these files are in your repository:
- `render.yaml` (backend deployment)
- `render-frontend.yaml` (frontend deployment)
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`

### Step 2: Deploy Database

Since Render doesn't support PostGIS, you have two choices:

#### Choice A: Use External PostGIS Database

**Recommended services:**
- **Aiven**: https://aiven.io (Free tier available)
- **ElephantSQL**: https://www.elephantsql.com (Free tier available)
- **Neon**: https://neon.tech (Free tier available)

Set up a PostGIS database on one of these services and use the connection string in your backend environment variables.

#### Choice B: Deploy Custom PostGIS on Render

Create a new Web Service on Render:
1. **Name**: `urban-mapper-db`
2. **Environment**: Docker
3. **Dockerfile**:
   ```dockerfile
   FROM postgis/postgis:16-3.4
   ENV POSTGRES_USER=walknet
   ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
   ENV POSTGRES_DB=walknet
   EXPOSE 5432
   ```
4. **Environment Variables**:
   - `POSTGRES_PASSWORD`: Generate a secure password

**Note**: This will use your Render service hours.

### Step 3: Deploy Backend

1. **Connect GitHub repository** to Render
2. **Create new Web Service**
3. **Select Repository**: Your urban_mapper repo
4. **Configuration**:
   - **Name**: `urban-mapper-backend`
   - **Environment**: Docker
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Root Directory**: `backend`
   - **Region**: Choose closest to your users (us-west for Korea)

5. **Environment Variables**:
   ```
   DATABASE_URL=postgresql+psycopg2://walknet:PASSWORD@DATABASE_HOST:5432/walknet
   SECRET_KEY=<GENERATE_SECURE_KEY>
   CORS_ORIGINS=https://your-frontend-url.onrender.com
   DEFAULT_PROJECT_EPSG=3857
   FLASK_ENV=production
   ```

   Replace:
   - `DATABASE_HOST`: Your PostGIS database host
   - `PASSWORD`: Your database password

6. **Advanced Settings**:
   - **Health Check Path**: `/api/projects`
   - **Auto-Deploy**: Yes
   - **Service Details**:
     - **Plan**: Standard ($7/month minimum)

7. **Deploy**

### Step 4: Deploy Frontend

1. **Create new Static Site** on Render
2. **Configuration**:
   - **Name**: `urban-mapper-frontend`
   - **Environment**: Docker
   - **Dockerfile Path**: `frontend/Dockerfile`
   - **Root Directory**: `frontend`

3. **Environment Variables**:
   ```
   VITE_API_BASE_URL=https://your-backend-url.onrender.com/api
   VITE_VWORLD_API_KEY=your_vworld_api_key
   ```

4. **Deploy**

### Step 5: Configure CORS

After deployment, update backend environment variable:
```
CORS_ORIGINS=https://urban-mapper-frontend.onrender.com,https://urban-mapper-frontend.onrender.com/
```

### Step 6: Test Deployment

1. Visit your frontend URL
2. Check browser console for errors
3. Try drawing a sidewalk line
4. Try exporting data

---

## Alternative: Railway.app Deployment (Easier)

Railway makes PostGIS deployment simpler:

### Step 1: Create Project

1. Go to [railway.app](https://railway.app)
2. Sign up/in with GitHub
3. **New Project** → **Deploy from GitHub**
4. Select `urban_mapper` repository

### Step 2: Add PostgreSQL Database

1. In your Railway project, click **+ New**
2. **Database** → **PostgreSQL**
3. Railway automatically provisions PostgreSQL with PostGIS enabled
4. Click on the database service
5. Go to **Variables** tab
6. Copy the `DATABASE_URL` (format: `postgresql://postgres:PASSWORD@HOST:PORT/railway`)

### Step 3: Update for Railway Database

Update your `DATABASE_URL` to include `postgresql+psycopg2://` prefix:
```
postgresql+psycopg2://postgres:PASSWORD@HOST:PORT/railway
```

### Step 4: Deploy Backend

1. **Add Service** → **GitHub Repo** → Select `urban_mapper`
2. **Settings**:
   - **Root Directory**: `backend`
   - **Build Command**: (leave empty, Docker handles it)
   - **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:app`

3. **Variables**:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@HOST:PORT/railway
   SECRET_KEY=<GENERATE_SECURE_KEY>
   CORS_ORIGINS=https://your-app.up.railway.app
   DEFAULT_PROJECT_EPSG=3857
   FLASK_ENV=production
   ```

### Step 5: Deploy Frontend

1. **Add Service** → **Static Assets**
2. **Settings**:
   - **Build Path**: `frontend/dist`
   - **Railway will detect Vite and build automatically**

3. **Environment Variables**:
   ```
   VITE_API_BASE_URL=https://your-backend.up.railway.app/api
   VITE_VWORLD_API_KEY=your_vworld_api_key
   ```

Railway will:
- Auto-detect `package.json` in frontend folder
- Run `npm install` and `npm run build`
- Serve from `dist/` directory

### Step 6: Database Initialization

After first deployment:

1. Open Railway backend service
2. Go to **Deployments**
3. Click on the latest deployment
4. Open **View Logs**
5. Look for PostGIS initialization messages

Or manually run migrations:
```bash
railway run flask db upgrade
```

---

## Environment Variables Reference

### Backend

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string with PostGIS | `postgresql+psycopg2://...` |
| `SECRET_KEY` | ✅ Yes | Flask secret key | Generate secure random string |
| `CORS_ORIGINS` | ✅ Yes | Allowed frontend URLs | `https://app.onrender.com` |
| `FLASK_ENV` | ⚠️ | Environment mode | `production` |
| `DEFAULT_PROJECT_EPSG` | No | CRS for storage | `3857` |

### Frontend

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_API_BASE_URL` | ✅ Yes | Backend API URL | `https://api.onrender.com/api` |
| `VITE_VWORLD_API_KEY` | No | V-World API key | Get from vworld.kr |

---

## Troubleshooting

### Issue: Database connection fails

**Solution**: 
- Verify `DATABASE_URL` format includes `postgresql+psycopg2://`
- Ensure PostGIS extensions are enabled (check logs for "CREATE EXTENSION")
- Check database is accessible from backend service

### Issue: CORS errors

**Solution**:
- Verify `CORS_ORIGINS` includes your frontend URL exactly
- Include trailing slash variations
- Check backend logs for CORS errors

### Issue: Frontend can't reach backend

**Solution**:
- Verify `VITE_API_BASE_URL` is correct
- Ensure backend health check passes
- Check both services are deployed

### Issue: PostGIS functions not working

**Solution**:
- Verify database has PostGIS enabled: `CREATE EXTENSION IF NOT EXISTS postgis;`
- Check SFCGAL is installed: `CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;`
- Review backend logs for PostGIS errors

### Issue: Export fails or downloads empty file

**Solution**:
- Check `geopandas` is installed in backend
- Verify database has data
- Check backend logs for export errors
- Ensure `MAX_EXPORT_SIZE` isn't exceeded

---

## Cost Estimates

### Render.com
- **Backend Web Service**: $7/month (Standard plan minimum)
- **Frontend Static Site**: Free
- **Custom PostGIS DB**: $7/month (if deploying custom container)
- **Total**: ~$14/month minimum

### Railway.app
- **Hobby Plan**: $5/month + usage
- **PostgreSQL with PostGIS**: Included in hobby plan
- **Total**: ~$10-15/month

### DigitalOcean App Platform
- **Basic App**: $5/month
- **Managed PostgreSQL**: $12/month (lowest tier)
- **Total**: ~$17/month

---

## Post-Deployment Checklist

- [ ] Database extensions enabled (PostGIS, SFCGAL)
- [ ] Backend health check passing
- [ ] Frontend loads without console errors
- [ ] Can draw sidewalk lines
- [ ] Data saves to database
- [ ] Export downloads valid GeoPackage
- [ ] CORS working (no browser errors)
- [ ] Basemap loading correctly
- [ ] Performance acceptable at expected user count

---

## Scaling Considerations

### For Multiple Students Working Simultaneously

1. **Database**: Upgrade to larger instance
2. **Backend**: Increase worker count in `gunicorn.conf.py`
3. **Monitoring**: Set up logging and error tracking (e.g., Sentry)
4. **Caching**: Add Redis for session management if needed
5. **CDN**: Use Cloudflare for frontend assets

### Optimizations

- **Connection Pooling**: Configure SQLAlchemy pool settings
- **Geometry Indexing**: Ensure spatial indexes on `geom` columns
- **Query Optimization**: Add pagination where needed
- **Asset Optimization**: Minify and compress frontend assets

---

## Support

If you encounter issues:
1. Check application logs in Render/Railway dashboard
2. Review browser console for frontend errors
3. Verify all environment variables are set correctly
4. Test database connectivity
5. Review this guide's troubleshooting section

For PostGIS-specific issues, refer to PostGIS documentation: https://postgis.net/

