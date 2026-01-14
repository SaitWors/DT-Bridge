import logging

logger = logging.getLogger("discord_adapter")

class DiscordAdapter:
    def __init__(self, bot, mapper):
        self.bot = bot
        self.mapper = mapper
        self.bridge_tag = "[BRIDGE-TG]"

    async def on_message(self, message):
        # игнорирую сообщения от ботов
        if message.author.bot:
            return

        # проверяем маппинг: есть ли мост для этого канала на telegram
        entry = self.mapper.get_bridge_for_discord_channel(message.channel.id)
        if not entry:
            return

        text = f"{self.bridge_tag} [D] {message.author.display_name}: {message.content}"
        if message.attachments:
            for att in message.attachments:
                text += f"\n[Attachment] {att.url}"

        # отправляем через mapper/telegram
        await self.mapper.send_to_telegram(entry, text)
