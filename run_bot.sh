#!/bin/bash
# Kill any old bot instance
pkill -9 -f "python -m bot" 2>/dev/null
sleep 1

# Clear logs
> /home/ironman2711/Desktop/leach-bot/log.txt
> /home/ironman2711/Desktop/leach-bot/bot_runtime.log

cd /home/ironman2711/Desktop/leach-bot

echo "=== BOT STARTING $(date) ===" | tee -a bot_runtime.log

# Run bot — both stdout and stderr go to bot_runtime.log AND to terminal
exec .venv/bin/python -m bot 2>&1 | tee -a bot_runtime.log
