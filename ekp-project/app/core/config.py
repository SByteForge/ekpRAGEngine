from pydantic import BaseSettings

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Enterprise Knowledge Platform"
    app_version: str = "1.0.0"
    
    # Database settings
    db_url: str
    db_name: str
    db_user: str
    db_password: str
    
    # Qdrant settings
    qdrant_url: str
    qdrant_api_key: str
    
    # Logging settings
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()