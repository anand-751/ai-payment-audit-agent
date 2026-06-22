from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Payment Audit Agent"

    DB_PATH: str = "app/db/payment_audit.db"

    SMTP_EMAIL: str = ""

    SMTP_PASSWORD: str = ""

    RECIPIENT_EMAIL: str = ""

    GROQ_API_KEY: str = ""

    JWT_SECRET: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()