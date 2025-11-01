# Simple Deployment Guide - Urban Network Mapper

Railway turned out to be overly complex for this setup. Here are better alternatives that actually work.

## 🏆 Best Options (Ranked)

### 1. DigitalOcean App Platform (Easiest - Recommended)

**Why**: PostGIS built-in, Docker Compose support, simple deployment

**Cost**: ~$17/month  
**Time**: 15 minutes  
**Setup**: Fully automated

#### Steps:

1. **Create Account**: https://www.digitalocean.com
2. **Create App**: Apps → Create App → GitHub
3. **Select Repo**: `dakoyaki/urban-network-mapper`
4. **Auto-detect**: DigitalOcean detects docker-compose.yml
5. **Configure**:
   - Backend: Port 8000
   - Frontend: Port 5173
   - Database: postgis/postgis:16-3.4
6. **Add Environment Variables**:

   **Backend**:
   ```
   DATABASE_URL=postgresql+psycopg2://walknet:walknet@db:5432/walknet
   SECRET_KEY=6517e71ad046667d67a424c09995982a05653431c80daad2e921db28cc86fad3
   FLASK_ENV=production
   CORS_ORIGINS=*
   ```

   **Frontend**:
   ```
   VITE_API_BASE_URL=https://your-app-url.ondigitalocean.app/api
   ```

7. **Deploy**: Click Deploy
8. **Done!** Your app is live

---

### 2. Render.com with Docker Compose

**Why**: Simpler than Railway, supports Docker Compose

**Cost**: $7/month minimum  
**Time**: 20 minutes  
**Setup**: Mostly automated

#### Steps:

1. **Create Account**: https://render.com
2. **Create Web Service**:
   - Environment: Docker Compose
   - Select your GitHub repo
   - Render reads docker-compose.yml
3. **Configure Environment Variables** (same as above)
4. **Deploy**

Render doesn't support Docker Compose in Web Services, so alternative:

#### Render Alternative (Separate Services):

1. **Create PostgreSQL**: Database → PostgreSQL with PostGIS template
2. **Create Backend**: Web Service → Docker → backend/Dockerfile
3. **Create Frontend**: Static Site → Build from frontend/
4. Configure environment variables
5. Link services

---

### 3. Fly.io (Great for Docker Compose)

**Why**: Excellent Docker Compose support, global edge

**Cost**: ~$10-15/month  
**Time**: 20 minutes  
**Setup**: CLI-based

#### Steps:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Deploy your Docker Compose setup
flyctl launch --copy-config

# Configure secrets
flyctl secrets set DATABASE_URL=...
flyctl secrets set SECRET_KEY=...
flyctl secrets set CORS_ORIGINS=*

# Deploy
flyctl deploy
```

---

### 4. AWS LightSail + Docker Compose

**Why**: Full control, predictable pricing

**Cost**: ~$12/month  
**Time**: 30 minutes  
**Setup**: Manual but straightforward

#### Steps:

1. **Create Instance**: Ubuntu 22.04
2. **SSH into instance**
3. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```
4. **Install Docker Compose**:
   ```bash
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   ```
5. **Clone repo**:
   ```bash
   git clone https://github.com/dakoyaki/urban-network-mapper.git
   cd urban-network-mapper
   ```
6. **Configure environment**: Edit docker-compose.yml to expose ports
7. **Start**:
   ```bash
   docker-compose up -d
   ```
8. **Configure firewall**: Allow ports 80, 443, 8000, 5173

---

### 5. Hetzner VPS + Docker Compose

**Why**: Cheapest, most control

**Cost**: ~$5/month  
**Time**: 30 minutes  
**Setup**: Manual

Same steps as AWS LightSail, cheaper server.

---

## 🎯 My Recommendation

**For your use case (educational project, students, Korean city mapping):**

### **Go with DigitalOcean App Platform**

**Reasons:**
- ✅ PostGIS works out of the box
- ✅ Docker Compose fully supported  
- ✅ Simple deployment
- ✅ Good documentation
- ✅ Educational credits available
- ✅ Reliable uptime
- ✅ $17/month is reasonable

**Alternative if on budget: Fly.io** - Also excellent Docker Compose support

---

## 🚫 Don't Use

- ❌ Railway (PostGIS issues)
- ❌ Heroku (no PostGIS support, expensive)
- ❌ Vercel/Netlify (wrong for this use case)

---

## 📋 Complete Docker Compose Setup

Your current `docker-compose.yml` is perfect! Just needs production tweaks:

### Production docker-compose.yml

```yaml
version: "3.9"
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      - POSTGRES_USER=walknet
      - POSTGRES_PASSWORD=${DB_PASSWORD:-walknet}
      - POSTGRES_DB=walknet
    volumes:
      - dbdata:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U walknet"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+psycopg2://walknet:${DB_PASSWORD:-walknet}@db:5432/walknet
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
      - CORS_ORIGINS=${CORS_ORIGINS:-*}
      - DEFAULT_PROJECT_EPSG=3857
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    expose:
      - "8000"

  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE_URL=${API_BASE_URL}
      - VITE_VWORLD_API_KEY=${V_WORLD_API_KEY}
    depends_on:
      - backend
    restart: unless-stopped
    expose:
      - "80"

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  dbdata:
```

---

## 🎓 For Students

Once deployed, share the frontend URL. They can:
- Access from any device
- Map their assigned area
- See each other's changes in real-time
- Export to GeoPackage

No login needed - completely open access.

---

## 💰 Cost Comparison

| Platform | Monthly Cost | PostGIS | Difficulty | Setup Time |
|----------|-------------|---------|------------|------------|
| DigitalOcean | $17 | ✅ Built-in | Easy | 15 min |
| Fly.io | $10-15 | ✅ Works | Medium | 20 min |
| AWS LightSail | $12 | ✅ Works | Medium | 30 min |
| Hetzner | $5 | ✅ Works | Hard | 30 min |
| Railway | $0-15 | ❌ Broken | Hard | ∞ |

---

## ✅ Next Steps

1. **Choose platform** (I recommend DigitalOcean)
2. **Deploy using their Docker Compose support**
3. **Configure environment variables**
4. **Test**
5. **Share with students**

Want me to create a specific guide for DigitalOcean? It's the fastest path to a working deployment.

