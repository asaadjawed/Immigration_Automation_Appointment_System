"""
Configuration settings for the application.
Loads environment variables and provides configuration.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/immigration_db"
    
    # Email Configuration (IMAP for receiving)
    EMAIL_HOST: str = "imap.gmail.com"
    EMAIL_PORT: int = 993
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_USE_SSL: bool = True
    
    # Email Configuration (SMTP for sending)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "" 
    SMTP_PASSWORD: str = ""  
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "" 
    
    # LLM Configuration (Gemini)
    GEMINI_OPEN_KEY: str = ""  
    LLM_PROVIDER: str = "gemini" 
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.3
    
    # Vector Database
    VECTOR_DB_PATH: str = "./vector_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Application
    APP_NAME: str = "Immigration Office Automation"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    GUIDELINES_DIR: str = "./guidelines"


# Global settings instance
settings = Settings()

