from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = str(BASE_DIR / "db" / "payment_audit.db")

class Settings(BaseSettings):

    APP_NAME: str = "Payment Audit Agent"

    DB_PATH: str = DEFAULT_DB
    
    GROQ_API_KEY: str = ""

    SMTP_EMAIL: str = ""

    SMTP_PASSWORD: str = ""

    RECIPIENT_EMAIL: str = ""

    JWT_SECRET: str = ""

    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
