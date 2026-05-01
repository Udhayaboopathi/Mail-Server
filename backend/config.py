from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    redis_url: str = Field(validation_alias="REDIS_URL")
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    mail_domain: str = Field(default="mail.yourdomain.com", validation_alias="MAIL_DOMAIN")
    maildir_base: str = Field(default="/var/mail", validation_alias="MAILDIR_BASE")
    max_message_size_mb: int = Field(default=25, validation_alias="MAX_MESSAGE_SIZE_MB")
    dkim_selector: str = Field(default="mail", validation_alias="DKIM_SELECTOR")
    dkim_private_key_path: str = Field(default="/etc/dkim/private.key", validation_alias="DKIM_PRIVATE_KEY_PATH")
    spamassassin_host: str = Field(default="spamassassin", validation_alias="SPAMASSASSIN_HOST")
    clamav_host: str = Field(default="clamav", validation_alias="CLAMAV_HOST")
    smtp_hostname: str = Field(default="mail.yourdomain.com", validation_alias="SMTP_HOSTNAME")
    enable_mail_servers: bool = Field(default=True, validation_alias="ENABLE_MAIL_SERVERS")
    cloudflare_api_token: str = Field(default="", validation_alias="CLOUDFLARE_API_TOKEN")
    encryption_secret_key: str = Field(default="", validation_alias="ENCRYPTION_SECRET_KEY")
    backup_passphrase: str = Field(default="", validation_alias="BACKUP_PASSPHRASE")
    backup_retention_days: int = Field(default=7, validation_alias="BACKUP_RETENTION_DAYS")
    invite_base_url: str = Field(default="https://yourdomain.com", validation_alias="INVITE_BASE_URL")
    tracking_base_url: str = Field(default="https://yourdomain.com/track", validation_alias="TRACKING_BASE_URL")
    tracking_enabled: bool = Field(default=True, validation_alias="TRACKING_ENABLED")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    ai_summary_enabled: bool = Field(default=True, validation_alias="AI_SUMMARY_ENABLED")
    ai_smart_reply_enabled: bool = Field(default=True, validation_alias="AI_SMART_REPLY_ENABLED")
    ai_priority_inbox_enabled: bool = Field(default=True, validation_alias="AI_PRIORITY_INBOX_ENABLED")
    ip_geo_url: str = Field(default="http://ip-api.com/json", validation_alias="IP_GEO_URL")
    ip_geo_token: str = Field(default="", validation_alias="IP_GEO_TOKEN")
    server_ip: str = Field(default="", validation_alias="SERVER_IP")
    frontend_url: str = Field(default="https://yourdomain.com", validation_alias="FRONTEND_URL")
    next_public_api_url: str = Field(default="https://yourdomain.com", validation_alias="NEXT_PUBLIC_API_URL")
    postgres_db: str = Field(default="emaildb", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="emailuser", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="change-this", validation_alias="POSTGRES_PASSWORD")

    @property
    def next_public_frontend_url(self) -> str:
        return self.frontend_url

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis_url

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.jwt_secret_key

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.jwt_algorithm


settings = Settings()
