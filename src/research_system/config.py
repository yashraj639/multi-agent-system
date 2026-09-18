"""Configuration settings for the Multi-Agent Research System."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openrouter_api_key: str = Field(
        default="",
        description="API key for OpenRouter LLM services",
    )
    tavily_api_key: str = Field(
        default="",
        description="API key for Tavily web search service",
    )
    model_name: str = Field(
        default="openrouter/free",
        description="LLM model identifier used across all components",
    )
    tavily_k: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of search results to retrieve from Tavily",
    )
    max_chars_per_page: int = Field(
        default=8000,
        ge=500,
        description="Maximum characters of text extracted per URL",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL for OpenRouter OpenAI-compatible API endpoint",
    )

    def validate_api_keys(self) -> None:
        """Validate that essential API keys are present."""
        missing = []
        if not self.openrouter_api_key or self.openrouter_api_key.startswith("your_"):
            missing.append("OPENROUTER_API_KEY")
        if not self.tavily_api_key or self.tavily_api_key.startswith("your_"):
            missing.append("TAVILY_API_KEY")

        if missing:
            raise ValueError(
                f"Missing or placeholder API keys in environment/.env: {', '.join(missing)}.\n"
                "Please configure real API keys in your .env file."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings."""
    return Settings()
