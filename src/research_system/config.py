"""Configuration settings for the Multi-Agent Research System."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    model_name: str = "openrouter/free"
    tavily_k: int = 5
    max_chars_per_page: int = 8000
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    def validate_api_keys(self) -> None:
        """Validate that essential API keys are present."""
        missing = []
        if not self.openrouter_api_key or self.openrouter_api_key.startswith("your_"):
            missing.append("OPENROUTER_API_KEY")
        if not self.tavily_api_key or self.tavily_api_key.startswith("your_"):
            missing.append("TAVILY_API_KEY")

        if missing:
            raise ValueError(f"Missing or placeholder API keys in .env: {', '.join(missing)}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
