import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("telegram_adapter")

class TelegramAdapter:
    def __init__(self, app, mapper, discord_adapter):
        self.app = app
        self.mapper = mapper
        self.discord_adapter = discord_adapter
        self.bridge_tag = "[BRIDGE-D]"

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_message is None:
            logger.debug("Сообщение пустое, игнорируем")
            return

        msg = update.effective_message
        chat_id = msg.chat_id
        
        logger.info(f"Получено сообщение из TG чата {chat_id}: {msg.text}")
        
        entry = self.mapper.get_bridge_for_telegram_chat(chat_id)
        if not entry:
            logger.warning(f"Мост для TG чата {chat_id} не найден в конфиге")
            return

        logger.info(f"Найден мост: TG {chat_id} -> Discord {entry['discord_channel_id']}")

        # Игнорируем сообщения от моста Discord -> Telegram
        if msg.text and "[BRIDGE-TG]" in msg.text:
            logger.info("Игнорируем bridged сообщение от Discord")
            return

        text = f"{self.bridge_tag} [T] {msg.from_user.full_name}: {msg.text or ''}"
        if msg.photo:
            text += "\n[Photo]"

        logger.info(f"Отправляем в Discord канал {entry['discord_channel_id']}: {text}")
        
        try:
            await self.mapper.send_to_discord(entry, text)
            logger.info("Сообщение успешно отправлено в Discord")
        except Exception as e:
            logger.error(f"Ошибка отправки в Discord: {e}", exc_info=True)