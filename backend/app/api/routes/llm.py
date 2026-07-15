from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import llm_headers
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.providers.llm.openai_provider import OpenAIExtractor
from app.schemas.chat import LlmConnectionResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config")
def config() -> dict[str, object]:
    settings = get_settings()
    return {
        "allow_user_provided_keys": settings.allow_user_provided_llm_keys,
        "server_key_configured": bool(settings.openai_api_key),
        "default_provider": settings.llm_provider,
        "default_model": settings.openai_default_model,
        "supported_extraction_modes": ["deterministic", "openai", "openai_with_fallback"],
    }


@router.post("/test", response_model=LlmConnectionResponse, responses={401: {"model": None}})
async def test_connection(headers: Annotated[tuple[str | None, str | None, object | None], Depends(llm_headers)]) -> LlmConnectionResponse | JSONResponse:
    _, model, user_key = headers
    settings = get_settings()
    key = user_key or (settings.openai_api_key if settings.allow_server_llm_key else None)
    selected_model = model or settings.openai_default_model
    if not key or not selected_model:
        raise AppError("LLM_CONFIGURATION_REQUIRED", "An OpenAI key and model are required.")
    try:
        await OpenAIExtractor(key, selected_model, settings.llm_request_timeout_seconds).test_connection()  # type: ignore[arg-type]
    except AppError as exc:
        return JSONResponse(status_code=exc.status_code, content={"connected": False, "provider": "openai", "error": {"code": exc.code, "message": exc.message}})
    return LlmConnectionResponse(connected=True, provider="openai", model=selected_model, message="The OpenAI connection was successful.")

