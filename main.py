import os
import logging
import asyncio
import discord
from discord.ext import commands
from telegram.ext import Application, MessageHandler, filters

from utils.logger_setup import setup_logging
from core.mapper import Mapper
from adapters.telegram_adapter import TelegramAdapter
from adapters.discord_adapter import DiscordAdapter

from dotenv import load_dotenv
import yaml

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ СРЕДЫ ПЕРВЫМ ДЕЛОМ
load_dotenv()
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# load config.yaml
with open("config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN не найден! Укажите в config.yaml или переменной окружения")
    exit(1)
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не найден! Укажите в config.yaml или переменной окружения")
    exit(1)

# --- Discord bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Mapper ---
mapper = Mapper(config=CONFIG)

# --- Discord adapter (Cog) ---
discord_adapter = DiscordAdapter(bot=bot, mapper=mapper, config=CONFIG)
# УБРАЛИ отсюда: bot.add_cog(discord_adapter)  # <-- УДАЛИТЬ ЭТУ СТРОКУ

# --- Telegram app ---
# Добавляем прокси поддержку (из config.yaml)
TELEGRAM_CONFIG = CONFIG.get("telegram", {})
builder = Application.builder().token(TELEGRAM_TOKEN)

# Если есть прокси в конфиге
proxy_url = TELEGRAM_CONFIG.get("proxy_url")
if proxy_url:
    logger.info(f"Используем прокси для Telegram: {proxy_url}")
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        proxy=proxy_url,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0
    )
    builder = builder.request(request)

telegram_app = builder.build()

telegram_adapter = TelegramAdapter(mapper=mapper, config=CONFIG)
telegram_app.add_handler(MessageHandler(filters.ALL, telegram_adapter.on_message))

# register clients in mapper
mapper.register_clients(discord_bot=bot, telegram_app=telegram_app)

# --- запуск: параллельно запускаем discord и telegram ---
async def run_bots():
    # 1. Добавляем ког для Discord (ТОЛЬКО ЗДЕСЬ!)
    await bot.add_cog(discord_adapter)
    
    # 2. Инициализируем Telegram
    await telegram_app.initialize()
    
    # 3. Запускаем Discord в фоне
    discord_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # 4. Запускаем Telegram
    await telegram_app.start()
    
    # 5. Для python-telegram-bot v20 используем run_polling
    try:
        await telegram_app.updater.start_polling(
            drop_pending_updates=True,
            timeout=30
        )
    except AttributeError:
        # Старая версия PTB
        await telegram_app.updater.start_polling()
    
    logger.info("Оба бота запущены!")
    
    # 6. Ждем завершения
    await discord_task

if __name__ == "__main__":
    try:
        asyncio.run(run_bots())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")