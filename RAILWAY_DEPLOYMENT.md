# Railway.app Deployment Guide - Urban Mapper

Complete step-by-step guide to deploy Urban Mapper on Railway.app.

## 🚀 Quick Start

**Time**: 15 minutes  
**Cost**: $5/month (free trial available)  
**Difficulty**: Easy  

---

## Prerequisites

- GitHub account
- Git repository with your code
- V-World API key (optional, for Korean maps)

---

## Step 1: Prepare Your Repository

Ensure your repository has these files:

```
urban_mapper/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── nixpacks.toml
│   └── ...
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── ...
├── railway.json
└── RAILWAY_DEPLOYMENT.md
```

---

## Step 2: Sign Up for Railway

1. Go to [railway.app](https://railway.app)
2. Click **Start a New Project**
3. **Sign up with GitHub** (recommended)
4. Authorize Railway to access your repositories

---

## Step 3: Create PostgreSQL Database

1. In Railway dashboard, click **+ New**
2. Select **Database** → **PostgreSQL**

Railway will automatically:
- Provision PostgreSQL with PostGIS enabled
- Generate secure credentials
- Create environment variables

3. **Copy the generated `DATABASE_URL`** - you'll need it

---

## Step 4: Deploy Backend

1. In Railway dashboard, click **+ New**
2. Select **GitHub Repo**
3. **Select your repository**: `urban_mapper`
4. Railway will start deploying

### Configure Backend Service

1. Click on your backend service
2. Go to **Variables** tab
3. Add these environment variables:

```bash
# Database (Railway auto-generates this, just confirm it exists)
DATABASE_URL=postgresql://postgres:PASSWORD@host:port/railway

# App Configuration
SECRET_KEY=<Generate a random secure key>

# Flask
FLASK_ENV=production

# CORS (set after frontend deploys)
CORS_ORIGINS=*

# Project Settings
DEFAULT_PROJECT_EPSG=3857
```

**Generate SECRET_KEY**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Configure Backend Settings

1. Go to **Settings** tab
2. **Root Directory**: `backend`
3. **Build Command**: Leave empty (Docker handles it)
4. **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:app`

### Add Health Check

1. In **Settings** → **Deploy** section
2. Add **Health Check**:
   - Path: `/api/projects`
   - Port: Auto-detect

---

## Step 5: Deploy Frontend

1. In Railway dashboard, click **+ New**
2. Select **GitHub Repo**
3. **Select your repository**: `urban_mapper`
4. Railway will detect it's a Vite app

### Configure Frontend Service

1. Go to **Settings** tab
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Start Command**: Leave empty (served as static site)

### Add Frontend Environment Variables

1. Go to **Variables** tab
2. Add:

```bash
# Backend API URL (replace with your backend URL)
VITE_API_BASE_URL=https://urban-mapper-backend-production.up.railway.app/api

# V-World API key (optional, for Korean basemaps)
VITE_VWORLD_API_KEY=your_key_here
```

**Important**: `VITE_API_BASE_URL` must use HTTPS!

### Configure Static Site

1. Go to **Settings** tab
2. Under **Static Assets**:
   - **Static Files**: `dist`
   - **Clean URLs**: Enabled

---

## Step 6: Update CORS Settings

After frontend deploys:

1. Get your frontend URL from Railway
2. Go to backend **Variables**
3. Update `CORS_ORIGINS`:

```bash
CORS_ORIGINS=https://urban-mapper-frontend-production.up.railway.app
```

Or allow all (for development):

```bash
CORS_ORIGINS=*
```

---

## Step 7: Custom Domain (Optional)

### Add Custom Domain

1. Go to frontend **Settings** → **Networking**
2. Click **Generate Domain** or **Add Domain**
3. Railway provides free SSL automatically

### Update API URL

After custom domain:

1. Update `VITE_API_BASE_URL` in frontend variables
2. Update `CORS_ORIGINS` in backend variables

---

## Step 8: Initialize Database

Railway should auto-initialize, but verify:

### Check Logs

1. Go to backend service
2. **Deployments** → Latest deployment
3. **View Logs**

Look for:
```
✓ PostGIS extension created
✓ Tables created
```

### Manual Initialization (if needed)

1. Go to backend service
2. **Deployments** → Latest deployment
3. Click **Shell**
4. Run:

```bash
flask db upgrade
```

---

## Step 9: Test Deployment

1. **Open frontend URL** in browser
2. **Check browser console** for errors
3. **Try these actions**:
   - ✓ Load map with basemap
   - ✓ Draw a sidewalk line
   - ✓ Save to database
   - ✓ Refresh page (data should persist)
   - ✓ Export GeoPackage

---

## Troubleshooting

### Issue: Frontend can't connect to backend

**Check**:
1. `VITE_API_BASE_URL` is set correctly
2. Backend is deployed and running
3. CORS is configured

**Fix**:
```bash
# In frontend variables
VITE_API_BASE_URL=https://your-backend-url.up.railway.app/api

# In backend variables
CORS_ORIGINS=https://your-frontend-url.up.railway.app
```

### Issue: Database connection fails

**Check**:
1. `DATABASE_URL` is in backend variables
2. Database service is running
3. Network connectivity

**Fix**:
```bash
# Re-create database if needed
# Railway auto-generates DATABASE_URL correctly
```

### Issue: PostGIS functions not working

**Check logs**:
```bash
# In backend Shell
flask shell
>>> from app.extensions import db
>>> db.session.execute("SELECT PostGIS_version()")
```

**Fix**: Railway should auto-enable PostGIS, but verify:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;
```

### Issue: Build fails

**Check**:
1. All required files are committed
2. Dockerfile is correct
3. Requirements.txt is valid

**Fix**: Check logs for specific error

### Issue: High costs

**Monitor**:
1. Railway dashboard → **Usage**
2. Check for excessive usage
3. Add resource limits

**Optimize**:
- Use caching
- Optimize queries
- Add pagination

---

## Monitoring

### View Metrics

1. **Dashboard**: Overview of all services
2. **Usage**: Resource consumption
3. **Logs**: Real-time application logs

### Set Up Alerts

1. **Project Settings** → **Notifications**
2. Configure alerts for:
   - High CPU usage
   - High memory usage
   - Deployment failures
   - Build failures

---

## Scaling

### Add Resources

1. **Service** → **Settings** → **Resources**
2. **CPU**: Increase if slow
3. **Memory**: Increase if OOM errors
4. **Add Replicas**: For high traffic

### Optimize Costs

1. **Use sleep mode**: For dev environments
2. **Set resource limits**: Prevent spikes
3. **Monitor usage**: Dashboard → Usage

---

## Team Collaboration

### Add Team Members

1. **Project Settings** → **Team**
2. **Invite Members**
3. Choose role:
   - **Owner**: Full access
   - **Admin**: Deploy + configure
   - **Developer**: View only

### Share Environment

1. **Service** → **Variables**
2. **Generate Public URL** (if needed)
3. Share carefully (contains secrets)

---

## Backup & Recovery

### Automatic Backups

Railway automatically backs up databases daily.

### Manual Backup

1. **Database** → **Data** → **Backup**
2. Download backup file
3. Store securely

### Restore from Backup

1. **Database** → **Data** → **Restore**
2. Upload backup file
3. Confirm restoration

---

## Cost Management

### Estimated Monthly Costs

| Resource | Plan | Cost |
|----------|------|------|
| Backend Service | Hobby | $0.013/hour |
| Frontend Service | Hobby | $0.013/hour |
| PostgreSQL (10GB) | Hobby | Included |
| **Typical Month** | | **$10-25** |

### Free Credits

- **$5 free credit** per month on Hobby plan
- **Usage**: First $5 is free
- **Overage**: Pay only for what you use

### Budget Alerts

1. **Settings** → **Usage**
2. Set **Spend Limit**
3. Configure alerts

---

## Maintenance

### Update Dependencies

1. Update `requirements.txt` or `package.json`
2. Commit changes
3. Railway auto-deploys

### Database Migrations

1. Update models
2. Create migration: `flask db migrate`
3. Apply: `flask db upgrade`

### Rollback

1. **Deployments** → Find good deployment
2. **Rollback** → Confirm

---

## Security Best Practices

### 1. Secure Secrets

✅ **Do**:
- Use Railway's secret management
- Rotate keys regularly
- Limit access to secrets

❌ **Don't**:
- Commit secrets to Git
- Share secrets in plain text
- Use simple passwords

### 2. CORS Configuration

✅ **Do**:
```bash
CORS_ORIGINS=https://your-domain.com
```

❌ **Don't**:
```bash
CORS_ORIGINS=*  # Only for development
```

### 3. Database Security

✅ **Do**:
- Use Railway's managed database
- Enable SSL
- Regular backups

### 4. API Security

✅ **Do**:
- Validate all inputs
- Rate limiting (add as needed)
- Error handling

---

## Next Steps

1. ✅ Deploy to Railway
2. ✅ Test all features
3. ✅ Add custom domain
4. ✅ Set up monitoring
5. ✅ Invite students
6. ✅ Monitor costs
7. ✅ Optimize performance

---

## Support

### Railway Resources

- 📖 [Documentation](https://docs.railway.app)
- 💬 [Discord](https://discord.gg/railway)
- 📧 [Email Support](mailto:support@railway.app)
- 🐛 [GitHub Issues](https://github.com/railwayapp)

### Urban Mapper Issues

- Check logs first
- Review this guide
- Consult DEPLOYMENT.md
- Check GitHub issues

---

## Success Checklist

- [ ] Backend deployed and running
- [ ] Frontend deployed and running
- [ ] Database connected with PostGIS
- [ ] Frontend can load map
- [ ] Can draw and save lines
- [ ] Data persists on refresh
- [ ] Export works
- [ ] CORS configured correctly
- [ ] Custom domain (optional)
- [ ] Team members added
- [ ] Monitoring configured
- [ ] Cost limits set

---

**You're ready to deploy! 🎉**

Follow this guide step-by-step, and your Urban Mapper will be live in 15 minutes.

