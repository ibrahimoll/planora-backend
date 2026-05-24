#.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str

    jwt_secret_code: str
    access_token_expire_minutes: int

    verification_code_secret: str
    verification_code_expire_minutes: int

    password_reset_code_secret: str
    password_reset_code_expire_minutes: int

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str

    email_provider: str = "smtp"
    brevo_api_key: str | None = None
    email_from_name: str = "Planora"

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

    firebase_enabled: bool = False
    firebase_credentials_path: str | None = None
    firebase_credentials_json: str | None = None

    deadline_reminder_scheduler_enabled: bool = False
    deadline_reminder_scheduler_interval_minutes: int = 30
    deadline_reminder_hours_ahead: int = 24
    deadline_reminder_include_overdue: bool = True

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
