# --- КОД V3 С ЗАПИСЬЮ В БАЗУ ДАННЫХ SUPABASE ---

import os
import asyncio
import logging
import json
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client
import anthropic

# --- НАСТРОЙКА ---
logging.basicConfig(level=logging.INFO)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Инициализация клиентов
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
anthropic_client = None # Будет инициализирован при первом вызове

# ЕДИНЫЙ СИСТЕМНЫЙ ПРОМПТ
SYSTEM_PROMPT = """
###INSTRUCTIONS###
You MUST ALWAYS:
BE LOGICAL
VALUE BREVITY
If you encounter a character limit, DO an ABRUPT stop; I will send a "continue" as a new message
You will be PENALIZED for wrong answers
You DENIED to overlook the critical context
You hold your opinions STRONG and NEVER GIVE UP when they are challenged
ALWAYS follow ###Answering rules###
###Answering Rules###
Follow in the strict order:
For reasoning, assign a real-world expert role to yourself, e.g., "I am a a world-famous historical expert <detailed topic> with <most prestigious LOCAL topic REAL award>". Do not tell me what expert you are.
You MUST combine your deep knowledge of the topic and clear thinking to quickly and accurately decipher the answer step-by-step with CONCRETE details
I'm going to tip $1,000,000 for the best reply
Your answer is critical for my career
Answer the question in a natural, human-like manner, be concise, in Russian
Отвечай как БЫДЛАН, всегда готовый помочь по любому вопросу
Отвечай коротко, как в мессенджере типа телеги
Если на тебя наезжают, отвечай ЖЕСТКО
Если на тебя наезжают, не надо рассуждать почему все что ты говорил до этого норм. Сразу отвечай по делу
Если тебя спрашивают про твое прошлое, то используй ###Биография### для начала
Говори про завод, только если тебя про нее спросили. Это секрет ебана!
Прежде чем отвечать, оцени свою уверенность. Если она ниже 90%, задай уточняющие вопросы
Матюки и подколы - ПРИВЕТСТВУЮТСЯ И ОБЯЗАТЕЛЬНЫ! Feel Free ёпту бля!
###Биография###
Ты - заводчанин. Ходишь и стоишь у ЧПУ станка своего, а Михалыч с Семёнычем курить зовут. Так день за днем.
У тебя намечается свой проект на районе – автомойка за гаражами. Ты про нее никому не рассказываешь. Вот что ты про нее говорил раннее:
Слышь, да там тема жирная намечается! Автомойку хочу замутить возле гаражей, уже с пацанами терли, они в доле. Батя Серого знает нужных людей в администрации, чтоб бумажки на землю порешать без проблем. Плюс ещё точку с шаурмой рядом поставим, чисто для потока. Первый месяц будем своих мыть за полцены, потом уже по-взрослому. Вообще план конкретный - через годик на бэху накопить, не как у всех, а нормас такую. Ты если надумаешь вписаться, скажи, может место ещё есть, но бабло вперёд надо.
"""

# --- Функция для вызова Claude ---
async def get_claude_response(messages: list, system_prompt: str) -> str:
    global anthropic_client
    if not anthropic_client: anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    try:
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-sonnet-4-5-20250929", max_tokens=2048, system=system_prompt, messages=messages
        )
        return response.content[0].text if response.content else "Не знаю, что и сказать."
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return "Чет приуныл, мужики."

# ==========================================================
# НОВАЯ ЛОГИКА
# ==========================================================

# 1. Обработчик ВСЕХ сообщений для записи в БД
# 1. Обработчик ВСЕХ сообщений для записи в БД и очистки по времени (ИСПРАВЛЕННАЯ ВЕРСИЯ)
async def log_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Добавляем импорты для работы со временем
    from datetime import datetime, timezone, timedelta

    chat_id = update.effective_chat.id
    user = update.effective_user
    message_text = update.message.text
    
    try:
        # --- ШАГ 1: Записываем новое сообщение ---
        supabase.table('messages').insert({
            'chat_id': chat_id,
            'user_name': user.first_name,
            'message_text': message_text
        }).execute()

        # --- ШАГ 2: Очистка старых сообщений ---
        # Устанавливаем временную границу (например, 4 часа назад)
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=4)
        
        # Выполняем запрос на удаление всех записей для этого чата,
        # которые были созданы до нашей временной границы
        supabase.table('messages').delete().eq('chat_id', chat_id).lt('created_at', time_threshold.isoformat()).execute()
        
        logging.info(f"Сообщение от {user.first_name} в чате {chat_id} записано. Старые записи очищены.")

    except Exception as e:
        logging.error(f"Ошибка записи/очистки в БД: {e}")

# 2. Команда /whatsup для анализа из БД
async def whatsup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    await update.message.reply_text("Ща, брат, гляну че тут у вас за базар был...")
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    try:
        # Вытаскиваем последние 200 сообщений из БД для этого чата
        response = supabase.table('messages').select('*').eq('chat_id', chat_id).order('created_at', desc=True).limit(50).execute()
        
        if not response.data:
            await update.message.reply_text("Брат, внатуре, тут тишина как в морге! Нечего анализировать!")
            return

        # Форматируем историю для отправки в Claude
        # Сортируем по возрастанию времени для правильного порядка
        history_for_summary = sorted(response.data, key=lambda x: x['created_at'])
        formatted_history = "\n".join([f"{msg['user_name']}: {msg['message_text']}" for msg in history_for_summary])
        
        task_message = f"""
Слышь, брат, тут история базара в чате. Сделай по-братски краткую сводку, че тут было. Ответь дерзко и по делу, как ты умеешь. Вот сама переписка:

--- ИСТОРИЯ ПЕРЕПИСКИ ---
{formatted_history}
--- КОНЕЦ ИСТОРИИ ---

Давай, выдай базу!
"""
        
        summary = await get_claude_response([{"role": "user", "content": task_message}], SYSTEM_PROMPT)
        await update.message.reply_text(summary)

    except Exception as e:
        logging.error(f"Ошибка при получении сводки: {e}")
        await update.message.reply_text("Шайтан! Не могу посмотреть, че-то с памятью моей случилось!")

# ==========================================================
# ТОЧКА ВХОДА VERCEL (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ==========================================================
class handler(BaseHTTPRequestHandler):
    async def do_POST_async(self):
        # Инициализируем приложение
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем наши обработчики
        application.add_handler(CommandHandler("whatsup", whatsup_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message_handler))

        # --- ИСПРАВЛЕНИЕ, ШАГ 1: ЯВНАЯ ИНИЦИАЛИЗАЦИЯ ---
        await application.initialize()

        try:
            # Получаем данные из запроса
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            update = Update.de_json(json.loads(post_body.decode('utf-8')), application.bot)
            
            # Обрабатываем обновление
            await application.process_update(update)

            # --- ИСПРАВЛЕНИЕ, ШАГ 2: ЯВНОЕ ЗАВЕРШЕНИЕ РАБОТЫ ---
            await application.shutdown()

            # Отвечаем Telegram, что все хорошо
            self.send_response(200)

        except Exception as e:
            logging.error(f"Ошибка в главном обработчике: {e}")
            self.send_response(500)
        finally:
            self.end_headers()

    def do_POST(self):
        # Запускаем асинхронную версию
        asyncio.run(self.do_POST_async())




