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
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_expiry_hours: int = 24
    cors_origins: list[str] = ["http://127.0.0.1:8000", "http://localhost:8000"]
    wx_app_id: str = ""
    wx_app_secret: str = ""
    wx_pay_mch_id: str = ""
    wx_pay_api_key: str = ""
    wx_pay_notify_url: str = ""
    admin_password: str = "changeme"
    firecrawl_api_key: str = ""

    model_config = {"env_prefix": "SP_", "env_file": ".env"}


settings = Settings()
