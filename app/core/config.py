from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "asm-asset-discovery"
    app_env: str = "development"
    debug: bool = False

    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://asm:asm@db:5432/asm"

    jwt_secret_key: str = "useStrongerSecret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMeAdmin123!"
    admin_full_name: str = "Platform Admin"

    default_page_size: int = 20
    max_page_size: int = 100

    dns_timeout_seconds: int = 5

    # Celery / Redis
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    scan_max_retries: int = 3
    scan_retry_backoff_seconds: int = 2

    # When true, skip recovering jobs into Celery (used by pytest)
    testing: bool = False

    # Login rate limit (in-memory, per client IP)
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60


settings = Settings()
