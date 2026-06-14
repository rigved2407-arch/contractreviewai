import os
from pathlib import Path
from pydantic_settings import BaseSettings


SECRETS_DIR = Path("/run/secrets")


def _from_env_or_secret(name: str, default: str = "") -> str:
    """Read from env var first, then Docker secret file, then default."""
    val = os.environ.get(name)
    if val:
        return val
    secret_path = SECRETS_DIR / name.lower()
    if secret_path.is_file():
        return secret_path.read_text().strip()
    return default


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/contract_review.db"
    openai_api_key: str = ""
    openai_model: str = "llama-3.3-70b-versatile"
    openai_base_url: str = "https://api.groq.com/openai/v1"
    storage_dir: str = "./data/storage"
    max_upload_size_mb: int = 50
    cors_origins: list[str] = ["http://localhost:3000"]

    encryption_key: str = ""
    encryption_salt: str = "contract-review-ai-salt"
    encrypt_documents: bool = False

    auth_enabled: bool = False
    api_key: str = ""

    audit_enabled: bool = True
    data_retention_days: int = 365
    auto_delete_expired: bool = False

    llm_data_logging: bool = False
    llm_use_azure: bool = False
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    llm_redact_pii: bool = False

    dpdp_compliance: bool = False
    data_residency: str = "local"

    sentry_dsn: str = ""
    log_level: str = "INFO"

    app_name: str = "Contract Review AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # JWT Auth
    jwt_secret: str = "change-this-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    app_url: str = "http://localhost:3000"

    # SMTP / Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@contractreviewai.com"
    smtp_from_name: str = "Contract Review AI"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fall back to Docker secrets for sensitive fields
        self.openai_api_key = self.openai_api_key or _from_env_or_secret("OPENAI_API_KEY")
        self.encryption_key = self.encryption_key or _from_env_or_secret("ENCRYPTION_KEY")
        self.api_key = self.api_key or _from_env_or_secret("API_KEY")
        self.jwt_secret = self.jwt_secret or _from_env_or_secret("JWT_SECRET")
        self.smtp_user = self.smtp_user or _from_env_or_secret("SMTP_USER")
        self.smtp_password = self.smtp_password or _from_env_or_secret("SMTP_PASSWORD")
        self.sentry_dsn = self.sentry_dsn or _from_env_or_secret("SENTRY_DSN")
        self.azure_openai_key = self.azure_openai_key or _from_env_or_secret("AZURE_OPENAI_KEY")


settings = Settings()
