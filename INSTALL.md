# Installation Guide - Python 3.13 Compatible

## ✅ Fixed Installation for Python 3.13+

If you encountered `pydantic-core` build errors, we've fixed that! The project now uses a simplified configuration that works perfectly with Python 3.13.

## 🚀 Quick Install

```bash
# Navigate to project
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe/paraphrase_engine

# Install dependencies (use minimal requirements)
pip3 install -r requirements-minimal.txt

# Verify installation
python3 verify_config.py

# Start the bot!
python3 -m paraphrase_engine.main
```

## 📦 What Was Changed

### Problem
- Python 3.13 is very new
- `pydantic-core` doesn't have pre-built wheels yet
- Building from source requires Rust compiler

### Solution
- Created `requirements-minimal.txt` with only essential packages
- Simplified `config/settings.py` to use `python-dotenv` instead of `pydantic-settings`
- All functionality preserved, just simpler dependencies

## ✨ What's Included

The minimal installation includes:

- ✅ `python-telegram-bot` - Telegram bot framework
- ✅ `python-docx` - Document processing
- ✅ `google-generativeai` - Google Gemini AI
- ✅ `python-dotenv` - Environment configuration
- ✅ `structlog` - Logging
- ✅ `aiofiles` - Async file operations
- ✅ `httpx` - HTTP client
- ✅ `tenacity` - Retry logic

## 🧪 Verify Installation

```bash
python3 verify_config.py
```

You should see:
```
✅ Configuration loaded successfully!
✅ Telegram Bot Token: 7648679762:AAHz_mnzP...
✅ Google Gemini: AIzaSyBn19T5aXxr_TeB...
✅ 1 AI provider(s) ready
✅ All checks passed! Ready to run the bot.
```

## 🎯 Next Steps

1. **Start the bot:**
   ```bash
   python3 -m paraphrase_engine.main
   ```

2. **Test on Telegram:**
   - Find your bot
   - Send `/start`
   - Upload a .docx file
   - Send text fragments

## 🔧 Troubleshooting

### Still getting errors?

```bash
# Upgrade pip first
pip3 install --upgrade pip setuptools wheel

# Then install
pip3 install -r requirements-minimal.txt
```

### Want full features (Google Sheets, etc.)?

Once the bot is working, you can optionally add:
```bash
pip3 install gspread google-auth
```

### Check Python version

```bash
python3 --version
# Should show: Python 3.13.x
```

## ✅ Installation Complete!

You're ready to use your Paraphrase Engine bot!
