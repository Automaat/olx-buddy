"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/olxbuddy"

    # Security
    secret_key: str = "change-me-in-production"

    # AI
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Scraping
    scrape_rate_limit: int = 5
    use_proxies: bool = False

    # Optional
    telegram_bot_token: str | None = None


settings = Settings()
