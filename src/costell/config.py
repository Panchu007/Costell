"""Application settings loaded from environment variables and the project .env file."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Project metadata, LLM options, and data directory settings."""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project metadata
    project_name: str = "Costell"
    project_version: str = "0.1.0"
    debug: bool = False

    # LLM configuration
    LLM_MODEL_NAME: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: SecretStr | None = None

    # Data directories
    raw_data_dir: Path = _PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = _PROJECT_ROOT / "data" / "processed"
    sample_data_dir: Path = _PROJECT_ROOT / "data" / "sample"


settings = Settings()
