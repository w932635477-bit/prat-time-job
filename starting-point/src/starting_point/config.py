from pydantic import model_validator
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
    wx_pay_cert_path: str = ""
    wx_pay_key_path: str = ""
    wx_webhook_token: str = ""
    wx_webhook_aes_key: str = ""
    admin_password: str = "changeme"
    firecrawl_api_key: str = ""
    static_dir: Path = Path("")

    model_config = {"env_prefix": "SP_", "env_file": ".env"}

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if len(self.admin_password) < 8:
            raise ValueError("SP_ADMIN_PASSWORD must be at least 8 characters")
        if len(self.jwt_secret) < 16:
            raise ValueError("SP_JWT_SECRET must be at least 16 characters")
        return self


settings = Settings()
