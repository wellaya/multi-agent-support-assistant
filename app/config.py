from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "support_kb"

    safety_db_path: str = "storage/app.db"


settings = Settings()
