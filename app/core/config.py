from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Camping Agent Demo"
    app_version: str = "1.0.0"
    # database_url: str = "sqlite+aiosqlite:///./app.db"
    database_url: str
    openai_api_key: str
    openai_model: str
    openai_embedding_model: str = "text-embedding-3-small"
    ai_enabled: bool = False
    qdrant_url: str
    qdrant_api_key: str

    model_config = SettingsConfigDict(env_file=".env")  # 從專案根目錄的 .env 檔讀取

settings = Settings()