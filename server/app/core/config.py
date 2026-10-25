from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Used for encrypting platform credentials
    FERNET_KEY: str

    # Celery / Redis
    CELERY_BROKER_URL: str 
    CELERY_RESULT_BACKEND: str 

    # Groq
    GROQ_API_KEY: str | None = None
    GROQ_REQUIREMENT_MODEL: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()