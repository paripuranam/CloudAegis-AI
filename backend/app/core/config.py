"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://cloudaegis:cloudaegis@localhost:5432/cloudaegis_db"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # AWS
    aws_region: str = "us-east-1"
    aws_account_id: Optional[str] = None
    aws_use_mock_data: bool = False

    # OpenRouter
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "CloudAegis AI"
    openrouter_site_url: Optional[str] = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
