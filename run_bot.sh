#!/bin/bash

# Paraphrase Engine Bot Manager Script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Paraphrase Engine v1.0 - Bot Manager                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to check if bot is running
check_running() {
    if pgrep -f "main.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to stop bot
stop_bot() {
    echo "🛑 Stopping bot..."
    pkill -f "main.py"
    sleep 2
    if check_running; then
        echo "⚠️  Force stopping..."
        pkill -9 -f "main.py"
        sleep 1
    fi
    echo "✅ Bot stopped"
}

# Function to start bot
start_bot() {
    if check_running; then
        echo "⚠️  Bot is already running!"
        echo "   Use './run_bot.sh stop' to stop it first"
        echo "   Or use './run_bot.sh restart' to restart"
        exit 1
    fi
    
    echo "🚀 Starting bot..."
    cd "$SCRIPT_DIR"
    python3 main.py
}

# Function to check status
status_bot() {
    if check_running; then
        echo "✅ Bot is RUNNING"
        echo ""
        echo "Process details:"
        ps aux | grep "main.py" | grep -v grep
    else
        echo "❌ Bot is NOT running"
        echo ""
        echo "To start: ./run_bot.sh start"
    fi
}

# Main command handling
case "$1" in
    start)
        start_bot
        ;;
    stop)
        if check_running; then
            stop_bot
        else
            echo "❌ Bot is not running"
        fi
        ;;
    restart)
        if check_running; then
            stop_bot
            echo ""
            echo "⏳ Waiting 3 seconds..."
            sleep 3
        fi
        start_bot
        ;;
    status)
        status_bot
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the bot"
        echo "  stop    - Stop the bot"
        echo "  restart - Restart the bot"
        echo "  status  - Check if bot is running"
        echo ""
        echo "Example: ./run_bot.sh start"
        exit 1
        ;;
esac

