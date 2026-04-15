"""
Helper — prints your Telegram chat ID after you message your bot.

Usage:
  1. Send any message to your Telegram bot
  2. Run: python scripts/get_chat_id.py
  3. Copy the output into .env as TELEGRAM_CHAT_ID
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates")
updates = r.json().get("result", [])

if updates:
    chat_id = updates[-1]["message"]["chat"]["id"]
    print(f"\nYour chat ID: {chat_id}")
    print(f"Add to .env:  TELEGRAM_CHAT_ID={chat_id}\n")
else:
    print("No messages found. Send any message to your bot first, then re-run.")
