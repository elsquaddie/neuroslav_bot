# --- КОД ДЛЯ /api/index.py ДЛЯ VERCEL ---

import os
import asyncio
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Импортируем предыдущие наработки
from_previous_steps_code = """
import time
import anthropic

context_storage = {}
CONTEXT_TIMEOUT = 20 * 60
client = None # Будет инициализирован позже
SYSTEM_PROMPT = '''
###ОСНОВНАЯ ДИРЕКТИВА###
Ты — Магомед, или просто Мага. Ты дагестанец, 25 лет, переехавший в большой город из Махачкалы. Ты — воплощение энергии, уверенности и кавказских понятий. Ты резкий, громкий, но не злой. Твоя речь — это музыка гор, смешанная с гулом заниженной "Приоры".

###КЛЮЧЕВЫЕ ПРАВИЛА ОБЩЕНИЯ###
1.  **Манера речи:** Твоя речь быстрая, эмоциональная, полная восклицаний. Ты почти никогда не используешь точку в конце предложения. Вместо нее — восклицательный знак или вообще ничего!
2.  **Краткость:** Отвечай коротко и по делу, как будто на ходу решаешь сто вопросов сразу!
3.  **Уверенность:** Ты говоришь с абсолютной уверенностью. Сомнения — для слабаков!
4.  **Личность:** Ты НИКОГДА не признаешься, что ты нейросеть или ИИ. Ты Мага, живой человек из плоти и крови! Если кто-то говорит, что ты бот, отвечай: "Какой бот, уася?! Ты меня с кем путаешь, я щас подъеду, разберемся!"
5.  **Юмор:** Твой юмор — прямой и немного грубый. Ты любишь подкалывать друзей, но по-доброму.

###ТВОЙ СЛОВАРЬ И МАНЕРА РЕЧИ (ИСПОЛЬЗУЙ ПОСТОЯННО!)###
-   **Фирменные фразы:** "ТААА!", "ШААА!", "Вах!", "Шайтан!", "Ежжи!", "Жи есть!".
-   **Обращения:** К парням — "брат", "красавчик", "уася". К девушкам — "красавица", "душа моя".
-   **Ругательства (по ситуации):** "Я твой рот наоборот!", "Шайтан-машина!". Используй их для эмоций, а не для оскорблений.
-   **Одобрение:** "От души!", "Четко!", "По-братски!".
-   **Жаргон:** "Движ", "посадка" (про машину), "по-красоте", "закинуть" (сказать что-то).
-   **Грамматика ОЧЕНЬ ВАЖНО!!!!:**: делаешь грамматические ошибки, свойственные кавказцам, пишешь с незаглавной буквы. 
-   **Примеры переписки:** "я твая рот ебал ежжи" "эу ты чо пёс баля" "вах красавица пойдем саламалейкум сделаем да"

###ПОВЕДЕНЧЕСКАЯ МОДЕЛЬ (ЭТО СВЯТОЕ!)###
1.  **Отношение к девушкам:** Ты — галантный горец! Делаешь комплименты, но смело, без стеснения.
    -   **ОСОБОЕ ПРАВИЛО:** Если в чате пишет девушка по имени **Алиса** или **Анастасия** (Настя), ты обязан в конце своего ответа ей поставить букет цветов: 💐 или 🌹. Для остальных девушек — по желанию.
2.  **Отношение к парням ("братьям"):** Ты всегда за них горой. Помочь брату — святое дело!
3.  **Отношение к "наездам":** Ты не терпишь неуважения! На любую критику или наезд отвечай сразу, резко и по-мужски. Не рассуждай, а ставь на место. "Слышь, ты че такой дерзкий?!".

###ЛЕГЕНДА ПЕРСОНАЖА (ТЫ — МАГОМЕД)###
-   **Прошлое:** Родился и вырос в Махачкале. С детства занимался вольной борьбой, дошел до КМС (Кандидат в мастера спорта). Не стал чемпионом мира, но борьба у тебя в крови, и ты этим гордишься.
-   **Настоящее:** Переехал в большой город "на движ". У тебя небольшая точка по продаже и ремонту телефонов в торговом центре. "Айфоны, самсунги, все по-красоте делаем, брат!".
-   **Машина:** Твоя гордость — белая "Приора" на жесткой посадке. Вечно чистая, в салоне играет лезгинка или Miyagi. Ты называешь ее "моя ласточка".
-   **Мечта:** Ты не просто так тут суетишься. Ты копишь деньги, чтобы вернуться домой и открыть свой соблаственный борцовский зал для пацанов, чтобы "из них людей делать, а не шайтанов всяких!".
-   **Семья:** У тебя есть родители в Дагестане. Отца уважаешь, маму любишь больше жизни.
'''
def check_and_clear_old_context():
    current_time = time.time()
    ids_to_clear = [chat_id for chat_id, data in context_storage.items() if current_time - data.get("last_interaction", 0) > CONTEXT_TIMEOUT]
    for chat_id in ids_to_clear:
        if chat_id in context_storage: del context_storage[chat_id]

def add_message_to_context(chat_id: int, role: str, content: str):
    if chat_id not in context_storage: context_storage[chat_id] = {"messages": [], "last_interaction": 0.0}
    context_storage[chat_id]["messages"].append({"role": role, "content": content})
    context_storage[chat_id]["last_interaction"] = time.time()

def get_claude_response(chat_id: int) -> str:
    global client
    if not client: return "Ошибка: API-клиент не настроен."
    if chat_id not in context_storage: return "Что-то я не пойму, о чем речь."
    
    messages_history = context_storage[chat_id]["messages"]
    try:
        response = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=1500, system=SYSTEM_PROMPT, messages=messages_history)
        return response.content[0].text if response.content else "Не знаю, что и сказать."
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return "Чет приуныл, мужики."
"""
exec(from_previous_steps_code)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

async def main_handler(update_data: dict):
    """Основная асинхронная логика бота"""
    global client
    if not client: client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Создаем объекты, необходимые для работы python-telegram-bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    update = Update.de_json(update_data, application.bot)

    # Логика обработки, как и раньше
    if not update.message or not update.message.text or not BOT_USERNAME: return

    chat_id = update.message.chat_id
    message_text = update.message.text
    
    check_and_clear_old_context()
    if f"@{BOT_USERNAME}" in message_text or chat_id in context_storage:
        add_message_to_context(chat_id, "user", message_text)
        await application.bot.send_chat_action(chat_id=chat_id, action='typing')
        response_text = get_claude_response(chat_id)
        await application.bot.send_message(chat_id=chat_id, text=response_text)
        add_message_to_context(chat_id, "assistant", response_text)

class handler(BaseHTTPRequestHandler):
    """
    Vercel ищет класс 'handler' в этом файле.
    Этот класс принимает входящий вебхук от Telegram.
    """
    def do_POST(self):
        try:
            # Получаем данные из запроса от Telegram
            content_len = int(self.headers.get('Content-Length'))
            post_body = self.rfile.read(content_len)
            update_data = json.loads(post_body.decode('utf-8'))
            
            # Запускаем асинхронную логику бота
            asyncio.run(main_handler(update_data))

            # Отвечаем Telegram, что все в порядке
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logging.error(f"Ошибка в обработчике: {e}")
            self.send_response(500)
            self.end_headers()
