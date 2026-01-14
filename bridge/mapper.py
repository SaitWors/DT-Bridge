import logging

logger = logging.getLogger("mapper")

class BridgeMapper:
    def __init__(self, config):
        self.config = config
        # индексируем по telegram_chat_id и discord_channel_id
        self.by_tg = {}
        self.by_discord = {}
        for b in config.get("bridges", []):
            self.by_tg[b["telegram_chat_id"]] = b
            self.by_discord[b["discord_channel_id"]] = b

        self._send_to_telegram = None
        self._send_to_discord = None

    def get_bridge_for_telegram_chat(self, chat_id):
        return self.by_tg.get(chat_id)

    def get_bridge_for_discord_channel(self, channel_id):
        return self.by_discord.get(channel_id)

    async def send_to_telegram(self, entry, text):
        if not self._send_to_telegram:
            raise RuntimeError("Telegram sender not set on mapper")
        await self._send_to_telegram(entry["telegram_chat_id"], text)

    async def send_to_discord(self, entry, text):
        if not self._send_to_discord:
            raise RuntimeError("Discord sender not set on mapper")
        await self._send_to_discord(entry["discord_channel_id"], text)
