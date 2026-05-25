from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # PostgreSQL (async for API)
    database_url: str = "postgresql+asyncpg://mlbapi:mlbapi@localhost:5432/mlbapi"

    # PostgreSQL (sync for ingestion scripts)
    database_url_sync: str = "postgresql+psycopg2://mlbapi:mlbapi@localhost:5432/mlbapi"

    # MLB Stats API
    mlb_api_base_url: str = "https://statsapi.mlb.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
