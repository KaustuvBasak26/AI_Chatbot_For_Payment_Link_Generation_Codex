from typing import Annotated

from fastapi import Header, Request
from pydantic import SecretStr

from app.core.config import get_settings
from app.core.exceptions import AppError


async def llm_headers(
    request: Request,
    provider: Annotated[str | None, Header(alias="X-LLM-Provider")] = None,
    model: Annotated[str | None, Header(alias="X-LLM-Model")] = None,
    api_key: Annotated[str | None, Header(alias="X-LLM-API-Key")] = None,
) -> tuple[str | None, str | None, SecretStr | None]:
    settings = get_settings()
    if provider and provider != "openai":
        raise AppError("LLM_PROVIDER_UNSUPPORTED", "Only OpenAI extraction is supported.")
    if api_key and not settings.allow_user_provided_llm_keys:
        raise AppError("USER_LLM_KEYS_DISABLED", "User-provided OpenAI keys are disabled.", 403)
    if api_key and settings.app_env == "production" and request.url.scheme != "https" and request.client and request.client.host not in {"127.0.0.1", "::1", "localhost"}:
        raise AppError("INSECURE_LLM_KEY_TRANSPORT", "OpenAI keys require HTTPS in production.", 400)
    return provider, model, SecretStr(api_key) if api_key else None

