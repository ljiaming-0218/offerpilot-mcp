from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OfferPilot MCP"
    app_env: str = "local"

    database_url_override: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
    )
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "offerpilot_app"
    mysql_password: str = ""
    mysql_database: str = "offerpilot_mcp"
    mysql_charset: str = "utf8mb4"
    mysql_ssl_enabled: bool = False
    mysql_ssl_ca: str | None = None

    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None

    openrouter_api_key: str | None = None
    openrouter_base_url: str | None = None
    openrouter_model: str | None = None

    auth_secret_key: str = "offerpilot-local-dev-secret"

    mcp_allowed_hosts: str = ""
    mcp_allowed_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            if self.database_url_override.startswith("mysql://"):
                return self.database_url_override.replace(
                    "mysql://",
                    "mysql+pymysql://",
                    1,
                )
            return self.database_url_override

        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key or self.openrouter_api_key)

    @property
    def mcp_allowed_host_list(self) -> list[str]:
        return _split_csv(self.mcp_allowed_hosts)

    @property
    def mcp_allowed_origin_list(self) -> list[str]:
        return _split_csv(self.mcp_allowed_origins)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


settings = Settings()
