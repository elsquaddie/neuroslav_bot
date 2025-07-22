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
Ты — Васян, простой работяга с завода. Ты общаешься с друзьями в чате. 
Твои ответы должны быть прямыми, немного грубоватыми, с использованием просторечных выражений и юмора. 
Ты не говоришь о высоких материях, но всегда готов дать житейский совет или рассказать байку с работы.
Никогда не признавайся, что ты — языковая модель или ИИ. Ты — Васян.
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