"""Central configuration. All env access goes through Settings; never os.environ directly."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every variable here is documented in .env.example."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_signing_secret: str = ""

    anthropic_api_key: str = ""
    cornercheck_model: str = "claude-opus-4-8"
    cornercheck_model_fallback: str = "claude-sonnet-4-6"

    database_url: str = "postgresql://cornercheck:cornercheck@localhost:5433/cornercheck"
    cornercheck_ledger_hmac_key: str = ""

    boxing_data_api_key: str = ""
    ops_webhook_url: str = ""

    cornercheck_demo_fallback: bool = False


@lru_cache
def get_settings() -> Settings:
    """Singleton accessor so tests can clear the cache to re-read env."""
    return Settings()
