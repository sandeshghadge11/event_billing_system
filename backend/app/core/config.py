from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or backend/.env."""

    # Display name used by FastAPI docs and the health check endpoint.
    app_name: str = "Prasad FX Lights Billing API"
    # Environment marker for local/development/production style configuration.
    app_env: str = "development"
    # SQLAlchemy connection string. The default points to a local MySQL database.
    database_url: str = "mysql+pymysql://billing_user:billing_password@localhost:3306/event_billing"
    # Browser origin allowed to call the backend through CORS.
    frontend_origin: str = "http://127.0.0.1:5173"
    # Mail settings used by the invoice send-mail endpoint.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    send_mail: str = "sandeshghadge301@gmail.com"
    recv_mail: str = "sandeshghadge301@gmail.com"
    smtp_app_password: str = ""

    # Pydantic reads backend/.env automatically, so secrets/config do not need
    # to be hardcoded in Python files.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single shared settings instance imported by the rest of the backend.
settings = Settings()
