from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.db.models import Conversation, ConversationMessage, PaymentRequest
from app.providers.llm.openai_provider import OpenAIExtractor
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.payment import ExtractedPaymentDraft, ItemDraft
from app.services.deterministic_extractor import DeterministicExtractor, required_missing_fields
from app.services.payment_request_service import PaymentRequestService


class ChatService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.payments = PaymentRequestService(db, settings)

    async def handle(self, data: ChatRequest, user_key: SecretStr | None, model: str | None) -> ChatResponse:
        conversation = self.db.get(Conversation, data.conversation_id) if data.conversation_id else None
        if data.conversation_id and not conversation:
            raise AppError("CONVERSATION_NOT_FOUND", "Conversation was not found.", 404)
        if not conversation:
            conversation = Conversation()
            self.db.add(conversation)
            self.db.flush()
        messages = list(self.db.scalars(select(ConversationMessage).where(ConversationMessage.conversation_id == conversation.id).order_by(ConversationMessage.created_at)).all())
        recent = messages[-self.settings.llm_max_context_messages:]
        user_context = [message.content for message in recent if message.role == "user"]
        llm_context = [{"role": message.role, "content": message.content} for message in recent]
        now = datetime.now(ZoneInfo(self.settings.app_timezone))
        extraction_method, provider_name, used_model, fallback_used = "deterministic", None, None, False
        if data.use_llm_extraction:
            key = user_key or (self.settings.openai_api_key if self.settings.allow_server_llm_key else None)
            selected_model = model or self.settings.openai_default_model
            if not key:
                raise AppError("LLM_KEY_REQUIRED", "An OpenAI API key is required.", 400)
            if not selected_model:
                raise AppError("LLM_MODEL_REQUIRED", "An OpenAI model is required.", 400)
            try:
                draft = await OpenAIExtractor(key, selected_model, self.settings.llm_request_timeout_seconds).extract_payment_request(data.message, llm_context, now.date().isoformat(), self.settings.app_timezone)
                extraction_method, provider_name, used_model = "llm", "openai", selected_model
            except AppError as exc:
                transient = exc.code in {"LLM_RATE_LIMITED", "LLM_TEMPORARILY_UNAVAILABLE", "LLM_INVALID_OUTPUT"}
                if not data.allow_deterministic_fallback or not transient:
                    raise
                combined = " ".join([*user_context, data.message])
                draft = await DeterministicExtractor().extract_payment_request(combined, [], now.isoformat(), self.settings.app_timezone)
                fallback_used = True
        else:
            combined = " ".join([*user_context, data.message])
            draft = await DeterministicExtractor().extract_payment_request(combined, [], now.isoformat(), self.settings.app_timezone)
        draft.currency = draft.currency or "INR"
        draft.missing_fields = required_missing_fields(draft)
        current = self.db.scalar(select(PaymentRequest).where(PaymentRequest.conversation_id == conversation.id).order_by(PaymentRequest.created_at.desc()))
        payment_request = self.payments.merge_draft(current, draft) if current else self.payments.create_from_draft(conversation.id, draft)
        assistant_message = self._message(draft)
        self.db.add_all([
            ConversationMessage(conversation_id=conversation.id, role="user", content=data.message),
            ConversationMessage(conversation_id=conversation.id, role="assistant", content=assistant_message),
        ])
        self.db.commit()
        return ChatResponse(
            conversation_id=conversation.id, payment_request_id=payment_request.id,
            assistant_message=assistant_message, draft=self._draft_from_request(payment_request, draft),
            missing_fields=draft.missing_fields, ambiguities=draft.ambiguities, validation_errors=[],
            requires_clarification=bool(draft.missing_fields or draft.ambiguities),
            requires_confirmation=not draft.missing_fields and not draft.ambiguities,
            extraction_method=extraction_method, llm_provider=provider_name, llm_model=used_model,
            llm_fallback_used=fallback_used,
        )

    @staticmethod
    def _message(draft: ExtractedPaymentDraft) -> str:
        if draft.ambiguities:
            return f"Please clarify: {draft.ambiguities[0]}"
        missing = draft.missing_fields
        if missing:
            needs_price = any("unit_price" in field for field in missing)
            needs_quantity = any("quantity" in field for field in missing)
            needs_expiry = "expiration" in missing
            if needs_price and needs_expiry:
                return "What is the unit price, and how long should the payment link remain valid?"
            if needs_price:
                return "What is the unit price?"
            if needs_quantity:
                return "What quantity should I use for this item?"
            if needs_expiry:
                return "How long should the payment link remain valid?"
            return "Please provide the item, quantity, and unit price."
        return "I extracted the payment details. Review them and confirm when ready."

    @staticmethod
    def _draft_from_request(request: PaymentRequest, extracted: ExtractedPaymentDraft) -> ExtractedPaymentDraft:
        items = (
            [ItemDraft(name=item.name, quantity=item.quantity, unit_price_minor=item.unit_price_minor) for item in request.items]
            if request.items
            else extracted.items
        )
        return ExtractedPaymentDraft(
            customer={"name": request.customer_name, "email": request.customer_email, "phone": request.customer_phone},
            items=items,
            currency=request.currency, discount_minor=request.discount_minor, tax_minor=request.tax_minor,
            pay_by=request.pay_by, expires_at=request.expires_at, description=request.description,
            missing_fields=extracted.missing_fields, ambiguities=extracted.ambiguities,
        )
