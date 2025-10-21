"""
Configuration settings for Paraphrase Engine v1.0
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    
    # AI API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Google Sheets Configuration
    google_sheets_credentials_path: Optional[str] = None
    google_sheets_spreadsheet_id: Optional[str] = None
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Database Configuration
    database_url: str = "sqlite:///./paraphrase_engine.db"
    
    # Application Settings
    app_env: str = "development"
    log_level: str = "INFO"
    max_file_size_mb: int = 10
    file_retention_hours: int = 24
    temp_files_dir: str = "./temp_files"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    secret_key: str
    
    # AI Model Settings
    ai_temperature: float = 0.7
    ai_max_tokens: int = 2000
    ai_timeout_seconds: int = 30
    ai_retry_attempts: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'


# Create settings instance
def get_settings():
    """Get settings with proper .env file location"""
    import sys
    from pathlib import Path
    
    # Find .env file
    current_dir = Path(__file__).parent.parent
    env_file = current_dir / ".env"
    
    if env_file.exists():
        return Settings(_env_file=str(env_file))
    else:
        # Try to use environment variables only
        try:
            return Settings()
        except:
            raise FileNotFoundError(
                f".env file not found at {env_file}. "
                "Please copy env.example to .env and configure it."
            )

settings = get_settings()

# Ensure temp files directory exists
os.makedirs(settings.temp_files_dir, exist_ok=True)
