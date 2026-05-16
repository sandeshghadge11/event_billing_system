from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Prasad FX Lights Billing API"
    app_env: str = "development"
    database_url: str = "mysql+pymysql://billing_user:billing_password@localhost:3306/event_billing"
    frontend_origin: str = "http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
