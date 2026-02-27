"""
Unit tests for configuration and settings.

Tests the Settings classes from config/settings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDatabaseSettings:
    """Test DatabaseSettings configuration."""

    def test_default_values(self, monkeypatch):
        """Test default values when environment variables not set."""
        # Clear relevant env vars
        for var in ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]:
            monkeypatch.delenv(var, raising=False)

        # Import fresh to get defaults
        from config.settings import DatabaseSettings

        db = DatabaseSettings()

        assert db.host == "localhost"
        assert db.port == 5432
        assert db.user == "cleaning_user"
        assert db.database == "cleaning_email_db"

    def test_custom_values_from_env(self, monkeypatch):
        """Test values loaded from environment variables."""
        monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_USER", "custom_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret123")
        monkeypatch.setenv("POSTGRES_DB", "custom_db")

        from config.settings import DatabaseSettings

        db = DatabaseSettings()

        assert db.host == "db.example.com"
        assert db.port == 5433
        assert db.user == "custom_user"
        assert db.password == "secret123"
        assert db.database == "custom_db"

    def test_connection_string_format(self, monkeypatch):
        """Test connection string is properly formatted."""
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
        monkeypatch.setenv("POSTGRES_DB", "testdb")

        from config.settings import DatabaseSettings

        db = DatabaseSettings()

        expected = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert db.connection_string == expected

    def test_dsn_format(self, monkeypatch):
        """Test DSN string is properly formatted."""
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
        monkeypatch.setenv("POSTGRES_DB", "testdb")

        from config.settings import DatabaseSettings

        db = DatabaseSettings()

        assert "host=localhost" in db.dsn
        assert "port=5432" in db.dsn
        assert "dbname=testdb" in db.dsn
        assert "user=testuser" in db.dsn
        assert "password=testpass" in db.dsn


class TestRedisSettings:
    """Test RedisSettings configuration."""

    def test_default_values(self, monkeypatch):
        """Test default Redis values."""
        for var in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD"]:
            monkeypatch.delenv(var, raising=False)

        from config.settings import RedisSettings

        redis = RedisSettings()

        assert redis.host == "localhost"
        assert redis.port == 6379
        assert redis.db == 0
        assert redis.password is None

    def test_url_without_password(self, monkeypatch):
        """Test Redis URL without password."""
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        from config.settings import RedisSettings

        redis = RedisSettings()

        assert redis.url == "redis://localhost:6379/0"

    def test_url_with_password(self, monkeypatch):
        """Test Redis URL with password."""
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_PASSWORD", "redispass")

        from config.settings import RedisSettings

        redis = RedisSettings()

        assert redis.url == "redis://:redispass@redis.example.com:6380/1"


class TestClaudeSettings:
    """Test ClaudeSettings configuration."""

    def test_default_model(self, monkeypatch):
        """Test default Claude model."""
        monkeypatch.delenv("CLAUDE_MODEL", raising=False)

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.model == "claude-sonnet-4-20250514"

    def test_custom_model(self, monkeypatch):
        """Test custom Claude model from env."""
        monkeypatch.setenv("CLAUDE_MODEL", "claude-opus-4-20250514")

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.model == "claude-opus-4-20250514"

    def test_validate_with_valid_key(self, monkeypatch):
        """Test validation passes with valid API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key-12345")

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.validate() is True

    def test_validate_with_empty_key(self, monkeypatch):
        """Test validation fails with empty API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.validate() is False

    def test_validate_with_placeholder_key(self, monkeypatch):
        """Test validation fails with placeholder API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.validate() is False

    def test_max_tokens_default(self, monkeypatch):
        """Test default max tokens."""
        monkeypatch.delenv("CLAUDE_MAX_TOKENS", raising=False)

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.max_tokens == 4096

    def test_max_tokens_custom(self, monkeypatch):
        """Test custom max tokens from env."""
        monkeypatch.setenv("CLAUDE_MAX_TOKENS", "8192")

        from config.settings import ClaudeSettings

        claude = ClaudeSettings()

        assert claude.max_tokens == 8192


class TestAppSettings:
    """Test AppSettings configuration."""

    def test_default_values(self, monkeypatch):
        """Test default app settings."""
        for var in ["APP_ENV", "DEBUG", "LOG_LEVEL"]:
            monkeypatch.delenv(var, raising=False)

        from config.settings import AppSettings

        app = AppSettings()

        assert app.env == "development"
        assert app.debug is True
        assert app.log_level == "INFO"

    def test_production_environment(self, monkeypatch):
        """Test production environment settings."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")

        from config.settings import AppSettings

        app = AppSettings()

        assert app.env == "production"
        assert app.debug is False
        assert app.is_production is True
        assert app.is_development is False

    def test_development_environment(self, monkeypatch):
        """Test development environment detection."""
        monkeypatch.setenv("APP_ENV", "development")

        from config.settings import AppSettings

        app = AppSettings()

        assert app.is_development is True
        assert app.is_production is False

    def test_debug_true_variations(self, monkeypatch):
        """Test various truthy values for DEBUG."""
        for value in ["true", "True", "TRUE"]:
            monkeypatch.setenv("DEBUG", value)

            from config.settings import AppSettings

            app = AppSettings()

            assert app.debug is True, f"DEBUG={value} should be True"

    def test_debug_false_variations(self, monkeypatch):
        """Test various falsy values for DEBUG."""
        for value in ["false", "False", "FALSE", "0", "no"]:
            monkeypatch.setenv("DEBUG", value)

            from config.settings import AppSettings

            app = AppSettings()

            assert app.debug is False, f"DEBUG={value} should be False"


class TestSettingsValidation:
    """Test Settings validation methods."""

    def test_validate_success(self, monkeypatch):
        """Test validation succeeds with all required settings."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key")

        from config.settings import Settings

        settings = Settings()

        assert settings.validate() is True

    def test_validate_fails_without_db_password(self, monkeypatch):
        """Test validation fails without database password."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key")

        from config.settings import Settings

        settings = Settings()

        assert settings.validate() is False

    def test_validate_fails_without_api_key(self, monkeypatch):
        """Test validation fails without API key."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")

        from config.settings import Settings

        settings = Settings()

        assert settings.validate() is False

    def test_validate_fails_with_both_missing(self, monkeypatch):
        """Test validation fails with both password and API key missing."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")

        from config.settings import Settings

        settings = Settings()

        assert settings.validate() is False


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        from config.settings import Settings, get_settings

        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns the global instance."""
        from config.settings import get_settings
        from config.settings import settings as global_settings

        settings = get_settings()

        assert settings is global_settings
