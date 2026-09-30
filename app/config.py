"""Application configuration, loaded from environment variables."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/support_desk.db"
    )

    # Optional LLM mode. When OPENAI_API_KEY is empty the app uses the
    # built-in rule-based triage engine and needs no paid keys.
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
