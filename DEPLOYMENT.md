# Deployment Guide for Paraphrase Engine v1.0

## 📋 Prerequisites

Before deploying, ensure you have:

1. **Telegram Bot Token**: Create a bot via [@BotFather](https://t.me/botfather)
2. **AI API Keys**: At least one of:
   - OpenAI API key
   - Anthropic Claude API key
   - Google Gemini API key
3. **Server**: VPS or cloud instance with:
   - 2GB+ RAM
   - 10GB+ storage
   - Ubuntu 20.04+ or similar
4. **Domain** (optional): For webhooks and monitoring

## 🚀 Deployment Options

### Option 1: VPS Deployment (Recommended)

#### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

#### Step 2: Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd paraphrase_engine

# Create environment file
cp env.example .env
nano .env  # Edit with your configuration
```

#### Step 3: Configure Environment

Edit `.env` with your values:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
SECRET_KEY=$(openssl rand -hex 32)

# At least one AI provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Optional Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google-sheets-key.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_sheet_id
```

#### Step 4: Deploy

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify deployment
docker ps
```

### Option 2: Google Cloud Run

#### Step 1: Build and Push Image

```bash
# Configure gcloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build image
docker build -t gcr.io/YOUR_PROJECT_ID/paraphrase-engine:latest .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/paraphrase-engine:latest
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy paraphrase-engine \
  --image gcr.io/YOUR_PROJECT_ID/paraphrase-engine:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="TELEGRAM_BOT_TOKEN=your_token" \
  --set-env-vars="OPENAI_API_KEY=your_key" \
  --memory 2Gi \
  --timeout 900
```

### Option 3: Heroku Deployment

#### Step 1: Create Heroku App

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login and create app
heroku login
heroku create paraphrase-engine-app
```

#### Step 2: Configure

```bash
# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set OPENAI_API_KEY=your_key
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
```

#### Step 3: Deploy

```bash
# Deploy using container
heroku container:push web
heroku container:release web

# Check logs
heroku logs --tail
```

## 🔐 Security Configuration

### SSL/TLS Setup (for webhooks)

If using Telegram webhooks instead of polling:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Set webhook
curl -F "url=https://your-domain.com/webhook" \
     -F "certificate=@/etc/letsencrypt/live/your-domain.com/cert.pem" \
     https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook
```

### Firewall Configuration

```bash
# Allow necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 80/tcp   # HTTP (redirect to HTTPS)
sudo ufw enable
```

## 📊 Google Sheets Setup

### Step 1: Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Google Sheets API
4. Create service account:
   ```
   IAM & Admin → Service Accounts → Create Service Account
   ```
5. Download JSON key file

### Step 2: Configure Spreadsheet

1. Create new Google Spreadsheet
2. Share with service account email (found in JSON file)
3. Note the spreadsheet ID from URL

### Step 3: Deploy Credentials

```bash
# Create credentials directory
mkdir -p credentials

# Copy credentials file
cp ~/Downloads/service-account-key.json credentials/google-sheets-key.json

# Update .env
echo "GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google-sheets-key.json" >> .env
echo "GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id" >> .env
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup

```bash
# Backup data
tar -czf backup_$(date +%Y%m%d).tar.gz temp_files/ logs/ *.db

# Backup to remote storage
rsync -avz backup_*.tar.gz user@backup-server:/backups/
```

### Monitoring

#### Using Docker logs:
```bash
# View recent logs
docker-compose logs --tail=100

# Follow logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f paraphrase-engine
```

#### System monitoring:
```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Monitor processes
htop
```

## 🚨 Troubleshooting

### Common Issues

#### Bot not responding:
```bash
# Check if container is running
docker ps

# Check logs for errors
docker-compose logs paraphrase-engine

# Restart services
docker-compose restart
```

#### API errors:
```bash
# Verify API keys
docker-compose exec paraphrase-engine python test_providers.py

# Check rate limits in logs
docker-compose logs | grep -i "rate"
```

#### Memory issues:
```bash
# Increase memory limits in docker-compose.yml
services:
  paraphrase-engine:
    mem_limit: 4g
    memswap_limit: 4g
```

### Health Checks

```bash
# Manual health check
curl http://localhost:8000/health

# Check Telegram bot
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

## 📈 Scaling

### Horizontal Scaling

For high load, deploy multiple instances:

```yaml
# docker-compose.yml
services:
  paraphrase-engine:
    scale: 3  # Run 3 instances
```

### Load Balancing

Use nginx for load balancing:

```nginx
upstream paraphrase_backend {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://paraphrase_backend;
    }
}
```

## 🔧 Production Checklist

- [ ] Set `APP_ENV=production` in .env
- [ ] Configure strong `SECRET_KEY`
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log rotation
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Set up alerting (email/Slack)
- [ ] Document recovery procedures
- [ ] Test disaster recovery

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Check GitHub issues
4. Contact support team

## 🔗 Useful Links

- [Docker Documentation](https://docs.docker.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Heroku Container Registry](https://devcenter.heroku.com/articles/container-registry-and-runtime)
