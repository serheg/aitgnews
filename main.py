# main.py
import os
import feedparser
import google.generativeai as genai
import re
import time
import requests
from datetime import datetime

# --- НАСТРОЙКИ ---
RSS_URLS = [
    "https://meduza.io/rss2/all",
    "https://habr.com/ru/rss/hubs/all/",
    "https://www.theverge.com/rss/index.xml"
]
PROCESSED_POSTS_FILE = "processed_posts.txt"
# Уберем лимит постов, так как мы все равно группируем их в одно сообщение
# MAX_POSTS_PER_RUN = 0 

# --- Получаем секреты из GitHub Actions ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_telegram_message(text):
    """Отправляет текстовое сообщение в Telegram-канал."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("[!] Токен бота или ID канала не найдены. Пропускаем отправку в Telegram.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Ограничение Telegram на длину сообщения - 4096 символов.
    # Если текст длиннее, мы его обрежем.
    if len(text) > 4096:
        text = text[:4090] + "\n(...)"

    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        print("  [+] Сводное сообщение успешно отправлено в Telegram.")
    except requests.RequestException as e:
        print(f"  [!] Ошибка при отправке сообщения в Telegram: {e}")

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def load_processed_posts():
    if not os.path.exists(PROCESSED_POSTS_FILE): return set()
    with open(PROCESSED_POSTS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_posts(processed_ids):
    with open(PROCESSED_POSTS_FILE, 'w',
