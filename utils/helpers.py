import requests
import os
import yaml

def send_telegram_message(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")