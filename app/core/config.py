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

    backend_cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080,"
        "http://localhost:5500,"
        "http://127.0.0.1:5500"
    )
    cors_allow_credentials: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()  # pyright: ignore[reportCallIssue]

DATABASE_URL = settings.database_url