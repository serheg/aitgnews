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
"https://rss.datuan.dev/telegram/channel/casetapai",
   "https://rss.datuan.dev/telegram/channel/HelloAlesha",
   "https://rss.datuan.dev/telegram/channel/iSimplify",
   "https://rss.datuan.dev/telegram/channel/solokumi",
   "https://rss.datuan.dev/telegram/channel/erdman_ai",
   "https://rss.datuan.dev/telegram/channel/the_ai_architect",
   "https://rss.datuan.dev/telegram/channel/t2fmedia",
   "https://rss.datuan.dev/telegram/channel/gscrm",
   "https://rss.datuan.dev/telegram/channel/misha_davai_po_novoi",
   "https://rss.datuan.dev/telegram/channel/shromarketing",
   "https://rss.datuan.dev/telegram/channel/aihacki",
   "https://rss.datuan.dev/telegram/channel/dzenopulse",
   "https://rss.datuan.dev/telegram/channel/TochkiNadAI",
   "https://rss.datuan.dev/telegram/channel/prompt_design",
   "https://rss.datuan.dev/telegram/channel/gptdoit",
   "https://rss.datuan.dev/telegram/channel/NeuralProfit",
   "https://rss.datuan.dev/telegram/channel/neyroseti_dr",
   "https://rss.datuan.dev/telegram/channel/neuron_media",
   "https://rss.datuan.dev/telegram/channel/gptdoit",
   "https://rss.datuan.dev/telegram/channel/neurogen_news",
   "https://rss.datuan.dev/telegram/channel/denissexy",
   "https://rss.datuan.dev/telegram/channel/neiroit_world",
   "https://rss.datuan.dev/telegram/channel/v_neuro",
   "https://rss.datuan.dev/telegram/channel/sburyi",
   "https://rss.datuan.dev/telegram/channel/tips_ai",
   "https://rss.datuan.dev/telegram/channel/myspacet_ai",
   "https://rss.datuan.dev/telegram/channel/sergiobulaev",
   "https://rss.datuan.dev/telegram/channel/notboring_tech",
   "https://rss.datuan.dev/telegram/channel/nobilix",
  "https://rss.datuan.dev/telegram/channel/aiforproduct",
    "https://rss.datuan.dev/telegram/channel/apimonster_ai",
       "https://rss.datuan.dev/telegram/channel/n8n_farm",
   "https://rss.datuan.dev/telegram/channel/traficwebsansay",
      "https://rss.datuan.dev/telegram/channel/iisy_business",
         "https://rss.datuan.dev/telegram/channel/makeeai",
         "https://rss.datuan.dev/telegram/channel/Neuro_Modd",
            "https://rss.datuan.dev/telegram/channel/casetapai",
   "https://rss.datuan.dev/telegram/channel/neurocry"
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
    with open(PROCESSED_POSTS_FILE, 'w', encoding='utf-8') as f:
        for post_id in sorted(list(processed_ids)): f.write(post_id + '\n')

def get_post_id(entry):
    return entry.get('id', entry.link)

# --- Основная логика скрипта ---
if not GEMINI_API_KEY: raise ValueError("Ошибка: API-ключ GEMINI_API_KEY не найден!")
genai.configure(api_key=GEMINI_API_KEY)
# Используем более новую и быструю модель
model = genai.GenerativeModel('gemini-1.5-flash-latest')

print("Запуск RSS-бота для создания сводного поста...")
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

# Сортируем посты по дате, чтобы в сводке они шли в логичном порядке
try: all_new_posts.sort(key=lambda x: x.published_parsed, reverse=True)
except (AttributeError, TypeError): print("\nНе удалось отсортировать посты по дате.")

print(f"\nВсего найдено {len(all_new_posts)} новых постов. Начинаем генерацию пересказов...")

# *** НОВАЯ ЛОГИКА: СБОР ПЕРЕСКАЗОВ ***
summaries_list = []
processed_in_this_run = set()

for i, entry in enumerate(all_new_posts):
    title = entry.title
    link = entry.link
    description = clean_html(entry.summary)

    print(f"  [{i+1}/{len(all_new_posts)}] Обрабатываю: {title[:50]}...")

    try:
        # Новый, более строгий промпт
        prompt = f"Перескажи главную суть этого поста ОДНИМ коротким предложением. Пост: '{description}'"
        response = model.generate_content(prompt)
        # Убираем лишние переносы строк и пробелы из ответа модели
        summary_sentence = response.text.strip().replace('\n', ' ')
        
        # Формируем строку для итогового сообщения
        # Используем тире (•) для красивого списка
        summary_line = f"• {summary_sentence} <a href='{link}'>»</a>\n\n"
        summaries_list.append(summary_line)
        
        # Добавляем ID в набор для последующего сохранения
        processed_in_this_run.add(get_post_id(entry))
        
    except Exception as e:
        print(f"    [!] Ошибка при обработке поста '{title[:50]}...': {e}")
    
    time.sleep(1) # Небольшая задержка между запросами к API

# *** НОВАЯ ЛОГИКА: ФОРМИРОВАНИЕ И ОТПРАВКА ЕДИНОГО ПОСТА ***
if not summaries_list:
    print("\nНе удалось сгенерировать ни одного пересказа. Выход.")
    exit()

# Получаем текущую дату для заголовка
current_date = datetime.utcnow().strftime('%d.%m.%Y')
# Собираем все пересказы в один текст
final_summary_text = "\n".join(summaries_list)

# Формируем финальное сообщение
final_telegram_post = f"{final_summary_text}"

print("\n--- Итоговый пост для Telegram ---")
print(final_telegram_post)
print("---------------------------------")

# Отправляем одно большое сообщение
send_telegram_message(final_telegram_post)

# Обновляем файл с обработанными постами
processed_ids.update(processed_in_this_run)
save_processed_posts(processed_ids)
print(f"\nОбработка завершена. Всего в базе {len(processed_ids)} постов.")
