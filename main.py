# main.py
import os
import feedparser
import google.generativeai as genai
import re
import time
import requests

# --- НАСТРОЙКИ ---
# Добавьте сюда RSS-ленты, которые хотите отслеживать
RSS_URLS = [
    "https://meduza.io/rss2/all",
    "https://habr.com/ru/rss/hubs/all/",
    "https://www.theverge.com/rss/index.xml"
]
PROCESSED_POSTS_FILE = "processed_posts.txt" 
MAX_POSTS_PER_RUN = 5 # Ограничение на кол-во постов за один запуск, чтобы не спамить

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
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        print("  [+] Сообщение успешно отправлено в Telegram.")
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
    with open(PROCESSED_POSTS_FILE, 'w', encoding='utf-8') as f:
        for post_id in sorted(list(processed_ids)): f.write(post_id + '\n')

def get_post_id(entry):
    return entry.get('id', entry.link)

# --- Основная логика скрипта ---
if not GEMINI_API_KEY: raise ValueError("Ошибка: API-ключ GEMINI_API_KEY не найден!")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

print("Запуск RSS-бота с отправкой в Telegram...")
processed_ids = load_processed_posts()
print(f"Загружено {len(processed_ids)} ID уже обработанных постов.")

all_new_posts = []
for rss_url in RSS_URLS:
    print(f"\n--- Проверяем ленту: {rss_url} ---")
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [!] Ошибка парсинга: {feed.bozo_exception}")
            continue
        
        new_from_feed = 0
        for entry in feed.entries:
            if get_post_id(entry) not in processed_ids:
                all_new_posts.append(entry)
                new_from_feed += 1
        print(f"  [+] Найдено {new_from_feed} новых постов.")
    except Exception as e:
        print(f"  [!] Не удалось обработать ленту: {e}")

if not all_new_posts:
    print("\nИтог: Новых постов не найдено.")
    exit()

try: all_new_posts.sort(key=lambda x: x.published_parsed, reverse=True)
except (AttributeError, TypeError): print("\nНе удалось отсортировать посты по дате.")

if MAX_POSTS_PER_RUN > 0: all_new_posts = all_new_posts[:MAX_POSTS_PER_RUN]

print(f"\nВсего будет обработано {len(all_new_posts)} новых постов.")

for i, entry in enumerate(reversed(all_new_posts)):
    title = entry.title
    link = entry.link
    description = clean_html(entry.summary)

    print("\n" + "="*80)
    print(f"[{i+1}/{len(all_new_posts)}] Обрабатываю: {title}")

    try:
        prompt = f"Перескажи главную суть этого поста в 3-4 коротких тезисах. Отвечай на русском языке. Пост: '{description}'"
        response = model.generate_content(prompt)
        summary = response.text
        
        print("  [+] Пересказ от Gemini получен.")
        
        message_text = f"<b>{title}</b>\n\n{summary}\n\n<a href='{link}'>Читать оригинал</a>"
        send_telegram_message(message_text)
        
        processed_ids.add(get_post_id(entry))
    except Exception as e:
        print(f"  [!] Ошибка при обработке поста или отправке: {e}")
    
    print("="*80)
    time.sleep(2)

save_processed_posts(processed_ids)
print(f"\nОбработка завершена. Всего в базе {len(processed_ids)} постов.")
