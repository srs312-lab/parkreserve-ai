from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/parkreserve"
    redis_url: str = "redis://localhost:6379/0"
    poll_interval_seconds: int = 300
    recreation_gov_base_url: str = "https://www.recreation.gov"
    ridb_base_url: str = "https://ridb.recreation.gov/api/v1"
    ridb_api_key: Optional[str] = None
    default_alert_email: Optional[str] = None
    default_alert_phone: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_phone: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
