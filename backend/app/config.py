from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
