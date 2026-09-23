from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Camping Agent Demo"
    app_version: str = "1.0.0"
    # database_url: str = "sqlite+aiosqlite:///./app.db"
    database_url: str
    openai_api_key: str
    openai_model: str
    ai_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env")  # 從專案根目錄的 .env 檔讀取

settings = Settings()