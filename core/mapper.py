import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Mapper:
    def __init__(self, config=None):
        self.config = config or {}
        self.discord_bot = None
        self.telegram_app = None
        
    def register_clients(self, *, discord_bot = None, telegram_app = None):
        if discord_bot:
            self.discord_bot = discord_bot
            logger.info("Маппер зарегал дискорд бота")
            
        if telegram_app:
            self.telegram_app = telegram_app
            logger.info("Маппер зарегал телеграм")
            
    async def send_to_discord(self, channel_id: int, text: str):
        if not self.discord_bot:
            logger.error("Дискорд бот незарегестрирован в Маппере")
            return
        try:
            channel = await self.discord_bot.fetch_channel(int(channel_id))
            await channel.send(text)
            logger.info("Отправлено сообщение для Дискорд канала %s", channel_id)
        except Exception as e:
            logger.exception("Ошибка отправки в Дискорд %s", e)
            
    async def send_to_telegram(self, chat_id: int, text: str, bridge_config=None):
        if not self.telegram_app:
            logger.error("Телеграм незарегестрирован в Маппер")
            return
        
        try:
            # Если есть bridge_config, можно использовать настройки из него
            if bridge_config:
                telegram_config = bridge_config.get("telegram", {})
                filters = telegram_config.get("filters", {})
                
                # Проверяем фильтры
                if filters.get("ignore_commands", False) and text.startswith('/'):
                    logger.info("Пропускаем команду по фильтру")
                    return
            
            await self.telegram_app.bot.send_message(chat_id=int(chat_id), text=text)
            logger.info("Отправлено сообщение для Телеграм чата %s", chat_id)
        except Exception as e:
            logger.exception("Ошибка отправки сообщений в Телеграм: %s", e)
            