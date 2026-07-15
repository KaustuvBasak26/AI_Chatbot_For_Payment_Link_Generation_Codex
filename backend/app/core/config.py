from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PayLink Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./paylink.db"
    frontend_origin: str = "http://localhost:5173"
    app_timezone: str = "Asia/Kolkata"
    log_level: str = "INFO"
    payment_provider: Literal["mock", "razorpay"] = "mock"
    mock_payment_base_url: str = "http://localhost:5173/pay/mock"
    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None
    llm_provider: Literal["none", "openai"] = "none"
    openai_default_model: str = ""
    openai_api_key: SecretStr | None = None
    allow_user_provided_llm_keys: bool = True
    allow_server_llm_key: bool = True
    llm_request_timeout_seconds: float = 20
    llm_max_context_messages: int = 10
    llm_max_prompt_length: int = 5000
    supported_currencies: Annotated[tuple[str, ...], NoDecode] = ("INR",)

    @field_validator("supported_currencies", mode="before")
    @classmethod
    def parse_currencies(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(part.strip().upper() for part in value.split(",") if part.strip())
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
