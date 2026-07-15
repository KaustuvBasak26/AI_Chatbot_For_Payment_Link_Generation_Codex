from pydantic import BaseModel, Field

from app.schemas.payment import ExtractedPaymentDraft


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=5000)
    use_llm_extraction: bool = False
    allow_deterministic_fallback: bool = True


class ChatResponse(BaseModel):
    conversation_id: str
    payment_request_id: str
    assistant_message: str
    draft: ExtractedPaymentDraft
    missing_fields: list[str]
    ambiguities: list[str]
    validation_errors: list[dict[str, str]]
    requires_clarification: bool
    requires_confirmation: bool
    extraction_method: str
    llm_provider: str | None
    llm_model: str | None
    llm_fallback_used: bool


class LlmConnectionResponse(BaseModel):
    connected: bool
    provider: str
    model: str
    message: str

