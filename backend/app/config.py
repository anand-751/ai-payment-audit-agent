from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_DB = BASE_DIR / "db" / "payment_audit.seed.db"


class Settings(BaseSettings):
    APP_NAME: str = "Payment Audit Agent"

    # Local default. Railway overrides this via environment variable.
    DB_PATH: str = str(DEFAULT_DB)

    GROQ_API_KEY: str = ""

    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    RECIPIENT_EMAIL: str = ""

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()

print(f"Configured DB_PATH = {settings.DB_PATH}")