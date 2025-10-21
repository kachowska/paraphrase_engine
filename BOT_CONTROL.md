# Bot Control Guide

## ✅ Problem Solved!

The conflict error was caused by **multiple bot instances running simultaneously**. I've fixed this and created an easy-to-use bot manager script.

---

## 🎮 Easy Bot Control (Recommended)

Use the `run_bot.sh` script for simple bot management:

### Start the Bot
```bash
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe/paraphrase_engine
./run_bot.sh start
```

### Stop the Bot
```bash
./run_bot.sh stop
```

### Restart the Bot
```bash
./run_bot.sh restart
```

### Check Bot Status
```bash
./run_bot.sh status
```

---

## 🔧 Manual Control

### Start the Bot Manually
```bash
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe
python3 -m paraphrase_engine.main
```

### Stop the Bot (Ctrl+C)
Press `Ctrl+C` in the terminal where the bot is running

### Find Running Instances
```bash
ps aux | grep "paraphrase_engine.main" | grep -v grep
```

### Kill All Bot Instances
```bash
pkill -f "paraphrase_engine.main"
```

---

## ⚠️ Common Issues

### "Conflict: terminated by other getUpdates request"

**Cause:** Multiple bot instances are running

**Solution:**
```bash
./run_bot.sh stop
# Wait 3 seconds
./run_bot.sh start
```

Or manually:
```bash
pkill -f "paraphrase_engine.main"
sleep 3
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe
python3 -m paraphrase_engine.main
```

---

## 📱 Using Your Bot

Once the bot is running:

1. **Open Telegram**
2. **Search** for your bot
3. **Send** `/start`
4. **Upload** `.docx` file
5. **Send** text fragments (each on new line)
6. **Receive** paraphrased document

---

## 💡 Pro Tips

### Run in Background (keeps running after closing terminal)

**Option 1: Using nohup**
```bash
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe
nohup python3 -m paraphrase_engine.main > bot.log 2>&1 &
```

**Option 2: Using screen**
```bash
screen -S paraphrase_bot
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe
python3 -m paraphrase_engine.main
# Press Ctrl+A then D to detach
# To reattach: screen -r paraphrase_bot
```

### View Logs in Real-Time
```bash
tail -f paraphrase_engine.log
# Or
tail -f logs/operations.jsonl
```

---

## 🎯 Quick Commands Summary

| Action | Command |
|--------|---------|
| **Start** | `./run_bot.sh start` |
| **Stop** | `./run_bot.sh stop` |
| **Restart** | `./run_bot.sh restart` |
| **Status** | `./run_bot.sh status` |
| **View Logs** | `tail -f paraphrase_engine.log` |

---

## ✅ Your Bot is Ready!

Just run:
```bash
cd /Users/kachowska/Downloads/УЧЕБА/prog.obiektowe/paraphrase_engine
./run_bot.sh start
```

Then use it on Telegram! 🎉
