"""Load project settings from the .env file."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database and AI connection settings."""

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    app_api_key: SecretStr
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
