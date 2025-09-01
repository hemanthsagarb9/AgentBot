import os
from typing import Optional
from pydantic_settings import BaseSettings
from app.models import AppConfig


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost/pingsso"
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: str = "pingsso-artifacts"
    secrets_manager_prefix: str = "pingsso"
    
    # Langfuse
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    prompt_label: str = "prod"
    
    # External Services
    servicenow_url: Optional[str] = None
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None
    
    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    
    # Application
    app_name: str = "Ping SSO Onboarding Agent"
    app_version: str = "0.9.0"
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def get_app_config() -> AppConfig:
    """Get AppConfig from settings."""
    settings = get_settings()
    
    return AppConfig(
        database_url=settings.database_url,
        aws_region=settings.aws_region,
        langfuse_secret_key=settings.langfuse_secret_key,
        langfuse_public_key=settings.langfuse_public_key,
        langfuse_host=settings.langfuse_host,
        servicenow_url=settings.servicenow_url,
        servicenow_username=settings.servicenow_username,
        servicenow_password=settings.servicenow_password,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        s3_bucket=settings.s3_bucket,
        secrets_manager_prefix=settings.secrets_manager_prefix
    )
