# Quick Start Guide - Paraphrase Engine v1.0

## ⚡ Get Started in 5 Minutes

### Step 1: Clone & Navigate
```bash
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe/paraphrase_engine
```

### Step 2: Configure Environment
```bash
# Copy the example environment file
cp env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Minimum Required Configuration:**
```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
SECRET_KEY=generate_with_openssl_rand_hex_32

# At least ONE AI provider
OPENAI_API_KEY=sk-your_openai_key
# OR
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key
# OR
GOOGLE_API_KEY=your_google_key
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Test Configuration
```bash
python test_providers.py
```

### Step 5: Run the Bot
```bash
# Option A: Using Python directly
python -m paraphrase_engine.main

# Option B: Using the startup script
./start.sh

# Option C: Using Docker
docker-compose up -d
```

---

## 📱 Using the Bot

### 1. Find Your Bot on Telegram
Search for your bot using the username you set in @BotFather

### 2. Start a Session
```
/start
```

### 3. Upload Your Document
- Send a .docx file when prompted
- File must be under 10MB

### 4. Send Fragments to Paraphrase
- Enter each fragment on a new line
- Example:
```
This is the first fragment to paraphrase.
This is the second fragment to paraphrase.
This is the third fragment to paraphrase.
```

### 5. Receive Results
- Wait for processing (~2-5 minutes per fragment)
- Download your processed .docx file

---

## 🔧 Common Commands

### Check if bot is running
```bash
docker ps  # if using Docker
# or
ps aux | grep python  # if running locally
```

### View logs
```bash
# Docker
docker-compose logs -f

# Local
tail -f paraphrase_engine.log
tail -f logs/operations.jsonl
```

### Stop the bot
```bash
# Docker
docker-compose down

# Local
# Press Ctrl+C in the terminal
```

### Restart the bot
```bash
# Docker
docker-compose restart

# Local
# Stop with Ctrl+C, then run again:
python -m paraphrase_engine.main
```

---

## 🆘 Troubleshooting

### Bot not responding?
1. Check if the process is running
2. Verify your TELEGRAM_BOT_TOKEN in .env
3. Check logs for errors

### "No AI providers configured" error?
- Ensure at least one API key is set in .env:
  - OPENAI_API_KEY
  - ANTHROPIC_API_KEY
  - GOOGLE_API_KEY

### Document processing fails?
- Ensure your .docx file is valid
- Check that fragments exactly match text in the document
- Look for errors in logs/errors.jsonl

### Out of memory?
- Reduce MAX_FILE_SIZE_MB in .env
- Process fewer fragments at once
- Increase Docker memory limits

---

## 📊 Monitoring

### Check Google Sheets Logs (if configured)
1. Open your Google Sheet
2. Check tabs:
   - **Tasks**: Overall task status
   - **Operations**: Detailed operations
   - **Results**: Original vs paraphrased text
   - **Errors**: Error tracking

### Check Local Logs
```bash
# Operations log
tail -f logs/operations.jsonl | jq .

# Errors log
tail -f logs/errors.jsonl | jq .

# Results log
tail -f logs/results.jsonl | jq .
```

---

## 🔐 Security Checklist

- [ ] Never commit .env to Git
- [ ] Keep API keys secret
- [ ] Use strong SECRET_KEY
- [ ] Regularly rotate credentials
- [ ] Monitor usage to detect anomalies
- [ ] Set appropriate file size limits

---

## 📚 Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Deploy to production**: [DEPLOYMENT.md](DEPLOYMENT.md)
3. **Understand the architecture**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
4. **Check implementation status**: [REPOSITORY_INFO.md](REPOSITORY_INFO.md)

---

## 🎯 Getting API Keys

### Telegram Bot Token
1. Open Telegram and search for @BotFather
2. Send `/newbot`
3. Follow the prompts
4. Copy the API token

### OpenAI API Key
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API keys
4. Create new secret key

### Anthropic API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API keys
4. Create new API key

### Google Gemini API Key
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Create API key

### Google Sheets (Optional)
1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable Google Sheets API
4. Create service account
5. Download JSON credentials

---

## 💡 Pro Tips

- **Multiple AI Providers**: Configure all three for best results
- **Google Sheets**: Very helpful for monitoring and analytics
- **Docker**: Recommended for production deployment
- **Backups**: Regularly backup your .env and credentials/
- **Monitoring**: Set up alerts for errors in production

---

## 🚀 Production Deployment

For production deployment, use Docker:

```bash
# 1. Configure environment
cp env.example .env
nano .env  # Set APP_ENV=production

# 2. Build and deploy
docker-compose up -d

# 3. Verify deployment
docker-compose ps
docker-compose logs -f

# 4. Set up monitoring
# Add your monitoring solution here
```

---

## 📞 Support

If you encounter issues:

1. Check the logs first
2. Review this guide
3. Read the full documentation
4. Check GitHub issues (if applicable)

---

**Happy Paraphrasing!** 🎉
