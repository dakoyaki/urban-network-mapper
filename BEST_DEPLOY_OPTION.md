# Best Deployment Option for Urban Network Mapper

After extensive troubleshooting, here's what actually works:

## 🏆 Recommended Solution: VPS with Docker Compose

**Why this is best:**
- ✅ Works perfectly (same as local setup)
- ✅ Full control
- ✅ PostGIS guaranteed to work
- ✅ Simple deployment
- ✅ Cost-effective

---

## 🎯 Option 1: Hetzner VPS (CHEAPEST)

**Cost**: $5-10/month  
**Setup Time**: 30 minutes  
**Difficulty**: Medium

### Steps:

1. **Buy VPS**: https://www.hetzner.com
   - Location: Choose closest to Korea (Singapore/Japan)
   - OS: Ubuntu 22.04
   - Size: CX22 (2 vCPU, 4GB RAM) - €5/month

2. **SSH in and setup**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo usermod -aG docker $USER

   # Install Docker Compose
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose

   # Clone your repo
   git clone https://github.com/dakoyaki/urban-network-mapper.git
   cd urban-network-mapper

   # Set environment variables
   export API_BASE_URL=http://YOUR_SERVER_IP:8000/api
   export DB_PASSWORD=changeme_secure_password
   export SECRET_KEY=6517e71ad046667d67a424c09995982a05653431c80daad2e921db28cc86fad3

   # Deploy
   docker-compose -f docker-compose.prod.yml up -d

   # Check status
   docker-compose ps
   ```

3. **Configure firewall** (optional but recommended):
   ```bash
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

4. **Done!** Access at `http://YOUR_SERVER_IP`

---

## 🎯 Option 2: AWS LightSail (EASY)

**Cost**: $12/month  
**Setup Time**: 20 minutes  
**Difficulty**: Easy

### Steps:

1. **Create instance**: https://aws.amazon.com/lightsail/
   - OS: Ubuntu 22.04
   - Size: 1GB RAM, 1 vCPU
   - Location: ap-northeast-2 (Seoul) if available

2. **Follow same steps as Hetzner**

3. **Add static IP** in LightSail dashboard

4. **Done!**

---

## 🎯 Option 3: DigitalOcean Droplet (SIMPLE)

**Cost**: $12/month  
**Setup Time**: 20 minutes  
**Difficulty**: Easy

### Steps:

1. **Create droplet**: https://www.digitalocean.com/products/droplets
   - Image: Ubuntu 22.04
   - Size: Basic $12/month (1GB RAM, 1 vCPU)
   - Region: Singapore (closest to Korea)

2. **Follow Hetzner setup steps**

3. **Done!**

---

## 🎯 Option 4: Revert to Local Development

If deployment is too complex right now:

### Keep it local for class:

1. **Run on your machine**: `docker compose up -d`
2. **Create ngrok tunnel**:
   ```bash
   # Install ngrok
   brew install ngrok  # Mac
   
   # Create tunnel
   ngrok http 5173
   ```
3. **Share ngrok URL** with students
4. **Free** and works perfectly!

---

## 💡 Quick Comparison

| Option | Cost | Setup | Maintenance | Best For |
|--------|------|-------|-------------|----------|
| Hetzner | $5/mo | 30 min | Low | Budget |
| AWS/DigitalOcean | $12/mo | 20 min | Low | Simplicity |
| ngrok | Free | 5 min | None | Quick test |
| Railway | $0-15/mo | ∞ | High | ❌ Don't |

---

## 🚀 Recommended Next Steps

1. **Quick test**: Use ngrok for class next week
2. **Long-term**: Deploy to Hetzner VPS
3. **Budget**: Student can get Hetzner for €4/month

Your Docker Compose config is perfect - it just needs a proper host!

Want me to create detailed Hetzner setup guide?

