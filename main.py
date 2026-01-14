import asyncio
import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

#Для дискорда
import discord
from discord.ext import commands

#Для Телеграмма
from telegram import __version__ as ptb_version
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from bridge.discord_adapter import DiscordAdapter
from bridge.telegram_adapter import TelegramAdapter
from bridge.mapper import BridgeMapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bridge")

load_dotenv()

from pathlib import Path
print(">>> Тест загрузки .env")
print("cwd:", os.getcwd())
print("script folder:", Path(__file__).parent.resolve())
res = load_dotenv()  # можно вызвать снова, вернёт True/False
print("load_dotenv returned:", res)
print("DISCORD_TOKEN envvar:", bool(os.getenv("DISCORD_TOKEN")))
print("TELEGRAM_TOKEN envvar:", bool(os.getenv("TELEGRAM_TOKEN")))
# Для безопасности не выводим сами токены полностью, только наличие


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not DISCORD_TOKEN or not TELEGRAM_TOKEN:
    logger.error("Токены не обнаружены йоу")
    raise SystemExit(1)

#Заводин Конфиги
CONFIG_PATH = Path("config.example.yaml")
with CONFIG_PATH.open() as f:
    config = yaml.safe_load(f)
    
async def main():
    #Делаем дискорд ботика
    intents = discord.Intents.default()
    intents.message_content = True
    discord_bot = commands.Bot(command_prefix="!", intents=intents)
    
    #Телеграм app
    telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    #Конфиг mapper/bridge
    mapper = BridgeMapper(config)
    
    #Адаптеры
    discord_adapter = DiscordAdapter(discord_bot, mapper)
    telegram_adapter = TelegramAdapter(telegram_app, mapper, discord_adapter)
    
    async def _send_to_discord(channel_id, text):
        ch = discord_bot.get_channel(channel_id)
        if ch:
            await ch.send(text)
        else:
            logger.warning(f"Такой Дискорд канал не найден: {channel_id}")
    
    async def _send_to_telegram(chat_id, text):
        await telegram_app.bot.send_message(chat_id=chat_id, text=text)
        
    mapper._send_to_discord = _send_to_discord
    mapper._send_to_telegram = _send_to_telegram
    
    #Принимаем сообщения
    telegram_app.add_handler(MessageHandler(filters.ALL, telegram_adapter.on_message))
    
    #Обработчик Дискордика
    @discord_bot.event
    async def on_ready():
        logger.info(f"Дискорд Ботик Готов. Заходим как {discord_bot.user}")
        
    @discord_bot.event
    async def on_message(message):
        await discord_adapter.on_message(message)
        await discord_bot.process_commands(message)
        
    #Запуск петель
    await asyncio.gather(telegram_app.initialize(), discord_bot.login(DISCORD_TOKEN))
    
    #start apps
    telegram_task = asyncio.create_task(telegram_app.start())
    discord_task = asyncio.create_task(discord_bot.connect())
    
    #Ждун
    try:
        await asyncio.gather(telegram_task, discord_task)
    except asyncio.CancelledError:
        logger.info("Остановочка...")
    finally:
        await telegram_app.stop()
        await discord_bot.close()
if __name__ == "__main__":
    asyncio.run(main())