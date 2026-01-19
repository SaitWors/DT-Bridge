from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


# --- Enums (перечисления) для ограничения значений ---
class FormatStyle(str, Enum):
    """Стиль оформления сообщений"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    RICH = "rich"


class TimeFormat(str, Enum):
    """Формат отображения времени"""
    RELATIVE = "relative"   # "5 минут назад"
    ABSOLUTE = "absolute"   # "15:30, 12 марта 2024"
    BOTH = "both"           # "15:30 (5 минут назад)"


class MediaStrategy(str, Enum):
    """Стратегия обработки медиа"""
    DOWNLOAD = "download"   # Скачивать и переотправлять
    LINK = "link"           # Только ссылка на оригинал


# --- Основные модели ---
class DiscordConfig(BaseModel):
    """Конфигурация для Discord"""
    channel_id: int
    server_name: Optional[str] = "Неизвестный сервер"
    channel_name: Optional[str] = "Неизвестный канал"
    
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "ignore_bots": True,
            "ignore_commands": True,
            "max_length": 2000
        }
    )
    
    @validator('channel_id')
    def validate_channel_id(cls, v):
        """Discord ID каналов обычно длинные числа"""
        if v < 10**17:  # Минимальная длина Discord ID
            raise ValueError(f'Некорректный Discord channel_id: {v}. Должен быть длинным числом (например, 123456789012345678)')
        return v


class TelegramConfig(BaseModel):
    """Конфигурация для Telegram"""
    chat_id: int  # Отрицательный для групп/каналов
    chat_name: Optional[str] = "Неизвестный чат"
    
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "ignore_commands": True,
            "forward_from_groups": False
        }
    )
    
    @validator('chat_id')
    def validate_chat_id(cls, v):
        """Telegram chat_id может быть положительным (личка) или отрицательным (группа)"""
        if v == 0:
            raise ValueError('Telegram chat_id не может быть 0')
        return v


class BridgeConfig(BaseModel):
    """Конфигурация одного моста"""
    name: str = "Безымянный мост"
    enabled: bool = True
    
    discord: DiscordConfig
    telegram: TelegramConfig
    
    @validator('name')
    def validate_name(cls, v):
        """Название моста не должно быть пустым"""
        if not v.strip():
            raise ValueError('Название моста не может быть пустым')
        return v.strip()


class FormattingConfig(BaseModel):
    """Конфигурация форматирования сообщений"""
    style: FormatStyle = FormatStyle.RICH
    show_author_avatar: bool = True
    show_timestamp: bool = True
    show_channel_info: bool = True
    time_format: TimeFormat = TimeFormat.RELATIVE
    
    emojis: Dict[str, str] = Field(
        default_factory=lambda: {
            "discord_message": "💬",
            "telegram_message": "📱",
            "media_photo": "🖼️",
            "media_video": "🎬",
            "media_document": "📎",
            "link": "🔗",
            "reply": "↪️"
        }
    )
    
    @validator('emojis')
    def validate_emojis(cls, v):
        """Проверяем, что все необходимые ключи эмодзи присутствуют"""
        required_keys = ["discord_message", "telegram_message", "media_photo"]
        for key in required_keys:
            if key not in v:
                v[key] = "⚡"  # Значение по умолчанию если нет
        return v


class MediaConfig(BaseModel):
    """Конфигурация обработки медиа"""
    max_file_size_mb: int = Field(default=50, ge=1, le=100)  # от 1 до 100 МБ
    handling_strategy: MediaStrategy = MediaStrategy.DOWNLOAD
    cleanup_temp_files: bool = True
    
    supported_types: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "images": ["image/png", "image/jpeg", "image/webp", "image/gif"],
            "videos": ["video/mp4", "video/quicktime", "video/webm"],
            "audio": ["audio/mpeg", "audio/ogg", "audio/wav"],
            "documents": ["application/pdf", "text/plain", "application/zip"]
        }
    )
    
    @validator('max_file_size_mb')
    def reasonable_file_size(cls, v):
        """Ограничиваем максимальный размер файла"""
        if v > 100:
            raise ValueError('Максимальный размер файла не должен превышать 100 МБ для стабильности')
        return v


class AppConfig(BaseModel):
    """Полная конфигурация приложения"""
    app: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "DT Bridge",
        "update_interval_sec": 5,
        "timezone": "Europe/Moscow"
    })
    
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)
    media: MediaConfig = Field(default_factory=MediaConfig)
    
    bridges: List[BridgeConfig]
    
    logging: Dict[str, Any] = Field(default_factory=lambda: {
        "level": "INFO",
        "file": "logs/bridge.log",
        "max_size_mb": 10,
        "backup_count": 5
    })
    
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "link_previews": True,
        "message_threads": True,
        "user_mentions": True,
        "auto_translate": False
    })
    
    @validator('bridges')
    def at_least_one_bridge(cls, v):
        """Должен быть хотя бы один мост"""
        if not v:
            raise ValueError('Должен быть настроен хотя бы один мост')
        return v
    
    @validator('bridges')
    def unique_bridge_identifiers(cls, v):
        """Проверяем уникальность каналов и чатов"""
        discord_channels = []
        telegram_chats = []
        
        for bridge in v:
            d_id = bridge.discord.channel_id
            t_id = bridge.telegram.chat_id
            
            if d_id in discord_channels:
                raise ValueError(f'Discord канал {d_id} используется в нескольких мостах')
            if t_id in telegram_chats:
                raise ValueError(f'Telegram чат {t_id} используется в нескольких мостах')
            
            discord_channels.append(d_id)
            telegram_chats.append(t_id)
        
        return v