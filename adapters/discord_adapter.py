import logging
from discord.ext import commands
import discord

logger = logging.getLogger(__name__)
BRIDGE_TAG = "[BRIDGE-D]"

class DiscordAdapter(commands.Cog):
    def __init__(self, bot, mapper, config=None):
        self.bot = bot
        self.mapper = mapper
        self.config = config or {}

    @commands.Cog.listener()
    async def on_message(self, message):
        # Пропускаем сообщения от самого бота
        if message.author == self.bot.user:
            return
        
        # Получаем конфигурацию МОСТОВ (не channels!)
        bridges_config = self.config.get("bridges", [])
        
        for bridge in bridges_config:
            # Проверяем, включен ли мост
            if not bridge.get("enabled", True):
                continue
            
            # Получаем настройки Discord для этого моста
            discord_config = bridge.get("discord", {})
            discord_channel_id = discord_config.get("channel_id")
            
            # Проверяем, что ID есть и он совпадает
            if discord_channel_id and str(discord_channel_id) == str(message.channel.id):
                # Получаем настройки Telegram для этого моста
                telegram_config = bridge.get("telegram", {})
                telegram_chat_id = telegram_config.get("chat_id")
                
                if telegram_chat_id:
                    # Проверяем фильтры Discord если они есть
                    filters = discord_config.get("filters", {})
                    if filters.get("ignore_bots", False) and message.author.bot:
                        return
                    if filters.get("ignore_commands", False) and message.content.startswith("!"):
                        return
                    
                    await self.process_discord_message(message, telegram_chat_id, bridge)
                break  # Выходим после нахождения совпадения
    
    async def process_discord_message(self, message, telegram_chat_id, bridge_config):
        """Обработка и пересылка сообщения из Discord в Telegram"""
        try:
            # Форматирование текста
            bridge_tag = bridge_config.get("name", "Мост")
            
            # Берем настройки форматирования из конфига
            formatting = self.config.get("formatting", {})
            style = formatting.get("style", "standard")
            
            # Формируем сообщение
            if style == "minimal":
                text = f"{message.content}"
            elif style == "rich":
                # Более красивое форматирование
                emojis = formatting.get("emojis", {})
                text = f"{emojis.get('discord_message', '💬')} **{message.author.display_name}**:\n{message.content}"
                
                # Добавляем информацию о сервере/канале
                if formatting.get("show_channel_info", True):
                    text += f"\n\n`#{message.channel.name}`"
            else:  # standard
                text = f"**{message.author.display_name}**: {message.content}"
            
            logger.info(f"{BRIDGE_TAG} Пересылаем сообщение из Discord в Telegram: {text[:100]}...")
            
            # Отправляем через маппер (теперь с bridge_config!)
            if hasattr(self.mapper, 'send_to_telegram'):
                await self.mapper.send_to_telegram(
                    chat_id=telegram_chat_id,
                    text=text,
                    bridge_config=bridge_config  # <-- Добавьте это
                )
            else:
                # Альтернативный способ
                await self.send_via_telegram_bot(message, telegram_chat_id, text)
                
        except Exception as e:
            logger.error(f"{BRIDGE_TAG} Ошибка обработки сообщения: {e}")
    
    async def send_via_telegram_bot(self, discord_message, telegram_chat_id, text):
        """Альтернативный способ отправки через Telegram бота"""
        try:
            # Получаем Telegram бота из маппера
            if hasattr(self.mapper, 'telegram_bot'):
                telegram_bot = self.mapper.telegram_bot
            else:
                # Пытаемся получить из глобального контекста
                from main import telegram_app
                telegram_bot = telegram_app.bot
            
            # Отправляем сообщение
            await telegram_bot.send_message(
                chat_id=telegram_chat_id,
                text=text
            )
            
            logger.info(f"{BRIDGE_TAG} Сообщение отправлено в Telegram чат {telegram_chat_id}")
            
        except Exception as e:
            logger.error(f"{BRIDGE_TAG} Ошибка отправки в Telegram: {e}")