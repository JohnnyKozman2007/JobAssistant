import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    APP_NAME: str = "JobAssistant Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server settings
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # API Keys
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Timeouts
    REQUEST_TIMEOUT: int = 30
    SCRAPER_TIMEOUT: int = 60
    
    # Database (optional)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite3")
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
