"""
Simple configuration settings for Paraphrase Engine v1.0
Compatible with Python 3.13+ without pydantic-settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env file from project root
project_root = Path(__file__).resolve().parents[2]
env_file = project_root / ".env"

if env_file.exists():
    load_dotenv(env_file)
else:
    # Try loading from current directory
    load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # Telegram Bot Configuration
    # Support different env var names for different bots
    telegram_bot_token: str = os.getenv("PARAPHRASE_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN", "")
    
    # AI API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Google Sheets Configuration
    google_sheets_credentials_path: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
    google_sheets_spreadsheet_id: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./paraphrase_engine.db")
    
    # Application Settings
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    file_retention_hours: int = int(os.getenv("FILE_RETENTION_HOURS", "24"))
    temp_files_dir: str = os.getenv("TEMP_FILES_DIR", "./temp_files")
    
    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "")
    
    # AI Model Settings
    ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "2000"))
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    ai_retry_attempts: int = int(os.getenv("AI_RETRY_ATTEMPTS", "3"))
    
    def __init__(self):
        # Validate required settings
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required in .env file")
        
        # Generate a default secret key if not provided
        if not self.secret_key:
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
            print(f"WARNING: No SECRET_KEY provided, using generated key. Set SECRET_KEY in production!")
        
        # Ensure at least one AI provider is configured
        if not any([self.openai_api_key, self.anthropic_api_key, self.google_api_key]):
            raise ValueError("At least one AI provider API key is required")
        
        # Ensure temp files directory exists
        Path(self.temp_files_dir).mkdir(parents=True, exist_ok=True)


# Create settings instance
settings = Settings()

