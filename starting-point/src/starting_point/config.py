from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://direct.evolink.ai"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_thinking: bool = False
    database_path: Path = Path("starting_point.db")
    host: str = "127.0.0.1"
    port: int = 8000
    jwt_secret: str = ""
    jwt_expiry_hours: int = 24
    cors_origins: list[str] = ["*"]
    wx_app_id: str = ""
    wx_app_secret: str = ""

    model_config = {"env_prefix": "SP_", "env_file": ".env"}


settings = Settings()
