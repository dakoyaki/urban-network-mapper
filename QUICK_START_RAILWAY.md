# Quick Start: Deploy to Railway in 15 Minutes

**Recommended deployment service: Railway.app**

## Why Railway?

✅ Native PostGIS support (no setup!)  
✅ $5/month with free credits  
✅ Easy GitHub integration  
✅ Perfect for student collaboration  

---

## Prerequisites

- GitHub repository with your code
- Railway account (free signup)
- 15 minutes

---

## Step 1: Sign Up (2 minutes)

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub
4. Authorize Railway

**Done!** ✅

---

## Step 2: Create Database (1 minute)

1. Click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically includes PostGIS
3. Copy the `DATABASE_URL` from the Variables tab

**Done!** ✅

---

## Step 3: Deploy Backend (5 minutes)

1. Click **+ New** → **GitHub Repo** → Select your repo
2. Railway detects the `railway.json` config automatically
3. Go to **Variables** tab, add:

```bash
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
CORS_ORIGINS=*
DEFAULT_PROJECT_EPSG=3857
```

4. Wait for deployment (2-3 minutes)

**Done!** ✅

---

## Step 4: Deploy Frontend (5 minutes)

1. Click **+ New** → **GitHub Repo** → Select your repo again
2. This creates a separate frontend service
3. Go to **Settings**:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
4. Go to **Variables** tab, add:

```bash
VITE_API_BASE_URL=https://<your-backend-url>.up.railway.app/api
VITE_VWORLD_API_KEY=your_key_here
```

5. Get your backend URL from the backend service's **Settings** → **Networking**

6. Wait for deployment

**Done!** ✅

---

## Step 5: Update CORS (1 minute)

1. Copy your frontend URL
2. Go to backend **Variables**
3. Update `CORS_ORIGINS`:

```bash
CORS_ORIGINS=https://<your-frontend-url>.up.railway.app
```

4. Redeploy backend (triggered automatically)

**Done!** ✅

---

## Step 6: Test (1 minute)

1. Open your frontend URL
2. Try drawing a sidewalk
3. Refresh the page - data should persist!

**You're live!** 🎉

---

## Get Your URLs

Both services are now live. Railway gives you:
- Backend: `https://*.up.railway.app`
- Frontend: `https://*.up.railway.app`

Make them permanent with custom domains (optional).

---

## Troubleshooting

### Frontend can't reach backend

**Check**: `VITE_API_BASE_URL` is correct

**Fix**: Update to `https://backend-url.up.railway.app/api`

### CORS errors

**Check**: `CORS_ORIGINS` includes your frontend URL

**Fix**: Update in backend Variables

### Database connection fails

**Check**: `DATABASE_URL` exists in backend Variables

**Fix**: Railway generates it automatically - just verify it's there

### Still stuck?

1. Check logs in Railway dashboard
2. See full guide: `RAILWAY_DEPLOYMENT.md`
3. Read: `DEPLOYMENT_RECOMMENDATIONS.md`

---

## Cost

**First month**: $0 (free credits)  
**Ongoing**: $5-15/month typical  
**Per student**: ~$0.50/month  

---

## What's Next?

- ✅ Add custom domain (free SSL included)
- ✅ Invite students as team members
- ✅ Monitor usage and costs
- ✅ Set up alerts

**Full documentation**: See `RAILWAY_DEPLOYMENT.md`

---

## Success!

Your Urban Mapper is now:
- ✅ Live on the internet
- ✅ Accessible to all students
- ✅ Storing data in PostGIS
- ✅ Ready for collaboration

**Share the frontend URL with your students and start mapping!**

