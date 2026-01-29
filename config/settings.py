"""
Application settings management.

Loads configuration from environment variables with sensible defaults.
Uses python-dotenv for .env file support.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)


@dataclass
class DatabaseSettings:
    """PostgreSQL database configuration."""
    host: str = field(default_factory=lambda: os.getenv('POSTGRES_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('POSTGRES_PORT', '5432')))
    user: str = field(default_factory=lambda: os.getenv('POSTGRES_USER', 'cleaning_user'))
    password: str = field(default_factory=lambda: os.getenv('POSTGRES_PASSWORD', ''))
    database: str = field(default_factory=lambda: os.getenv('POSTGRES_DB', 'cleaning_email_db'))
    min_connections: int = field(default_factory=lambda: int(os.getenv('DB_MIN_CONNECTIONS', '2')))
    max_connections: int = field(default_factory=lambda: int(os.getenv('DB_MAX_CONNECTIONS', '10')))

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @property
    def dsn(self) -> str:
        """Build DSN format connection string for psycopg2."""
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


@dataclass
class RedisSettings:
    """Redis cache/queue configuration."""
    host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    db: int = field(default_factory=lambda: int(os.getenv('REDIS_DB', '0')))
    password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_PASSWORD'))

    @property
    def url(self) -> str:
        """Build Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class ClaudeSettings:
    """Anthropic Claude API configuration."""
    api_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    model: str = field(default_factory=lambda: os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514'))
    max_tokens: int = field(default_factory=lambda: int(os.getenv('CLAUDE_MAX_TOKENS', '4096')))

    def validate(self) -> bool:
        """Check if API key is configured."""
        if not self.api_key or self.api_key == 'your_anthropic_api_key_here':
            logger.error("ANTHROPIC_API_KEY is not configured")
            return False
        return True


@dataclass
class AppSettings:
    """General application settings."""
    env: str = field(default_factory=lambda: os.getenv('APP_ENV', 'development'))
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'true').lower() == 'true')
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    timezone: str = field(default_factory=lambda: os.getenv('TIMEZONE', 'America/New_York'))
    response_approval_mode: str = field(
        default_factory=lambda: os.getenv('RESPONSE_APPROVAL_MODE', 'manual')
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env == 'development'

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env == 'production'


@dataclass
class TelegramSettings:
    """Telegram bot configuration."""
    bot_token: str = field(
        default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', '')
    )
    admin_chat_id: str = field(
        default_factory=lambda: os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')
    )

    def is_configured(self) -> bool:
        """Check if Telegram bot is properly configured."""
        return bool(
            self.bot_token
            and self.bot_token != 'your_bot_token_from_botfather'
            and self.admin_chat_id
        )

    def validate(self) -> bool:
        """
        Validate Telegram settings.

        Returns:
            bool: True if settings are valid for operation
        """
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN is not set")
            return False
        if not self.admin_chat_id:
            logger.warning("TELEGRAM_ADMIN_CHAT_ID is not set")
            return False
        return True


@dataclass
class CalendarSettings:
    """Google Calendar integration configuration."""
    enabled: bool = field(
        default_factory=lambda: os.getenv('CALENDAR_ENABLED', 'false').lower() == 'true'
    )
    calendar_id: str = field(
        default_factory=lambda: os.getenv('GOOGLE_CALENDAR_ID', 'primary')
    )
    default_duration_hours: float = field(
        default_factory=lambda: float(os.getenv('CALENDAR_DEFAULT_DURATION', '3.0'))
    )
    buffer_minutes: int = field(
        default_factory=lambda: int(os.getenv('CALENDAR_BUFFER_MINUTES', '30'))
    )
    timezone: str = field(
        default_factory=lambda: os.getenv('CALENDAR_TIMEZONE', 'America/New_York')
    )

    def is_configured(self) -> bool:
        """Check if calendar integration is enabled and configured."""
        return self.enabled


@dataclass
class CRMSettings:
    """CRM integration configuration."""
    enabled: bool = field(
        default_factory=lambda: os.getenv('CRM_ENABLED', 'false').lower() == 'true'
    )
    provider: str = field(
        default_factory=lambda: os.getenv('CRM_PROVIDER', 'null')
    )
    api_key: str = field(
        default_factory=lambda: os.getenv('CRM_API_KEY', '')
    )
    api_url: str = field(
        default_factory=lambda: os.getenv('CRM_API_URL', '')
    )
    sync_enabled: bool = field(
        default_factory=lambda: os.getenv('CRM_SYNC_ENABLED', 'false').lower() == 'true'
    )
    log_interactions: bool = field(
        default_factory=lambda: os.getenv('CRM_LOG_INTERACTIONS', 'true').lower() == 'true'
    )

    def is_configured(self) -> bool:
        """Check if a real CRM provider is enabled and selected."""
        return self.enabled and self.provider != "null"


@dataclass
class FlaskSettings:
    """Flask web dashboard API configuration."""
    secret_key: str = field(
        default_factory=lambda: os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-me')
    )
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-me')
    )
    jwt_access_token_expires: int = field(
        default_factory=lambda: int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
    )
    jwt_refresh_token_expires: int = field(
        default_factory=lambda: int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800'))
    )
    frontend_url: str = field(
        default_factory=lambda: os.getenv('FRONTEND_URL', 'http://localhost:3000')
    )


@dataclass
class Settings:
    """
    Main settings container.

    Usage:
        from config.settings import settings

        # Access database settings
        conn_string = settings.database.connection_string

        # Access Claude settings
        api_key = settings.claude.api_key

        # Access Telegram settings
        bot_token = settings.telegram.bot_token

        # Access Calendar settings
        calendar_id = settings.calendar.calendar_id

        # Access CRM settings
        crm_enabled = settings.crm.is_configured()
    """
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    claude: ClaudeSettings = field(default_factory=ClaudeSettings)
    app: AppSettings = field(default_factory=AppSettings)
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    calendar: CalendarSettings = field(default_factory=CalendarSettings)
    crm: CRMSettings = field(default_factory=CRMSettings)
    flask: FlaskSettings = field(default_factory=FlaskSettings)

    def validate(self) -> bool:
        """
        Validate all required settings are configured.

        Returns:
            bool: True if all required settings are valid
        """
        errors = []

        # Check database password
        if not self.database.password:
            errors.append("POSTGRES_PASSWORD is not set")

        # Check Claude API key
        if not self.claude.validate():
            errors.append("ANTHROPIC_API_KEY is not configured")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True

    def configure_logging(self) -> None:
        """Configure logging based on settings."""
        log_level = getattr(logging, self.app.log_level.upper(), logging.INFO)

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            force=True  # Override any existing configuration
        )

        # Reduce noise from third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

        # Telegram library logging (set to INFO to see important events)
        logging.getLogger('telegram').setLevel(logging.INFO)
        logging.getLogger('telegram.ext').setLevel(logging.INFO)

        # Our services should log at configured level
        logging.getLogger('services.telegram').setLevel(log_level)

        if self.app.debug:
            logger.debug("Debug mode enabled")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings: The configured settings object
    """
    return settings


# Configure logging on import if this is the main settings module
if __name__ != '__main__':
    settings.configure_logging()
