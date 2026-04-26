from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    database_path: Path = Path("career_compass.db")
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_prefix": "CC_", "env_file": ".env"}


settings = Settings()
