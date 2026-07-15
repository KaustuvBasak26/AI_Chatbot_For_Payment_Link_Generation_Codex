from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, AuthenticationError, NotFoundError
from pydantic import SecretStr

from app.core.exceptions import AppError
from app.providers.llm.openai_provider import OpenAIExtractor


class FakeResponses:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.kwargs: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(output_parsed=self.result)


class FakeModels:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def retrieve(self, model: str) -> object:
        if self.error:
            raise self.error
        return SimpleNamespace(id=model)


def extractor_with(responses: FakeResponses | None = None, models: FakeModels | None = None) -> OpenAIExtractor:
    extractor = OpenAIExtractor(SecretStr("sk-test-not-real"), "gpt-test", 2)
    extractor.client = SimpleNamespace(responses=responses or FakeResponses(), models=models or FakeModels())  # type: ignore[assignment]
    return extractor


@pytest.mark.asyncio
async def test_structured_result_and_untrusted_totals_are_ignored() -> None:
    responses = FakeResponses({
        "customer": {"name": "Asha"},
        "items": [{"name": "Monitor", "quantity": 2, "unit_price_minor": 1500000, "line_total_minor": 1}],
        "currency": "INR",
        "validity_days": 7,
        "subtotal_minor": 1,
        "total_minor": 1,
    })
    draft = await extractor_with(responses=responses).extract_payment_request("two monitors", [], "2026-07-15", "Asia/Kolkata")
    assert draft.items[0].unit_price_minor == 1500000
    assert not hasattr(draft, "total_minor")
    assert responses.kwargs["store"] is False
    assert "Backend current date" in str(responses.kwargs["instructions"])


@pytest.mark.asyncio
async def test_connection_uses_model_retrieval() -> None:
    await extractor_with(models=FakeModels()).test_connection()


@pytest.mark.asyncio
async def test_authentication_and_model_errors_are_precise() -> None:
    request = httpx.Request("GET", "https://api.openai.com/v1/models/gpt-test")
    auth = AuthenticationError("bad key", response=httpx.Response(401, request=request), body=None)
    with pytest.raises(AppError) as auth_error:
        await extractor_with(models=FakeModels(auth)).test_connection()
    assert auth_error.value.code == "LLM_AUTHENTICATION_FAILED"

    missing = NotFoundError("missing", response=httpx.Response(404, request=request), body=None)
    with pytest.raises(AppError) as model_error:
        await extractor_with(models=FakeModels(missing)).test_connection()
    assert model_error.value.code == "LLM_MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_timeout_is_transient() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    with pytest.raises(AppError) as error:
        await extractor_with(responses=FakeResponses(error=APITimeoutError(request=request))).extract_payment_request("hello", [], "2026-07-15", "Asia/Kolkata")
    assert error.value.code == "LLM_TEMPORARILY_UNAVAILABLE"
