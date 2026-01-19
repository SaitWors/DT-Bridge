import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

BRIDGE_TAG = "[BRIDGE-TG]"

class TelegramAdapter:
    def __init__(self, mapper, config=None):
        self.mapper = mapper
        self.config = config or {}

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = update.effective_message
        if not msg or not msg.text:
            return

        text = msg.text.strip()
        if BRIDGE_TAG in text:
            return

        author = msg.from_user.first_name or "tg_user"
        formatted = f"[TG] {author}: {text} {BRIDGE_TAG}"

        bridge = None
        if self.config:
            for b in self.config.get("bridges", []):
                # Получаем chat_id из телеграм конфига моста
                telegram_config = b.get("telegram", {})
                telegram_chat_id = telegram_config.get("chat_id")
                if telegram_chat_id and int(telegram_chat_id) == int(update.effective_chat.id):
                    bridge = b
                    break

        if bridge:
            # Получаем discord channel_id из дискорд конфига моста
            discord_config = bridge.get("discord", {})
            discord_channel_id = discord_config.get("channel_id")
            if discord_channel_id:
                await self.mapper.send_to_discord(discord_channel_id, formatted)
            else:
                logger.warning("TelegramAdapter: no discord channel id in bridge for chat %s", update.effective_chat.id)
        else:
            logger.warning("TelegramAdapter: no bridge config for chat %s", update.effective_chat.id)