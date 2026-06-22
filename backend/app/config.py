from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Payment Audit Agent"

    DB_PATH: str = "app/db/payment_audit.db"

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