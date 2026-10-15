"""Load project settings from the .env file."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database connection settings."""

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )