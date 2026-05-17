from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_code: str
    access_token_expire_minutes: int

    verification_code_secret: str
    verification_code_expire_minutes: int

    password_reset_code_secret: str
    password_reset_code_expire_minutes: int

    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str

    google_client_id: str

    ai_provider: str = "local"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = 15
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]

DATABASE_URL = settings.database_url