import hashlib
import json
import secrets
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.db.models import IdempotencyRecord, PaymentItem, PaymentLink, PaymentRequest, RequestStatus
from app.providers.payments.base import PaymentProvider
from app.schemas.payment import ExtractedPaymentDraft, PaymentRequestOut, PaymentRequestUpdate
from app.services.payment_calculator import calculate_totals

EDITABLE = {RequestStatus.DRAFT, RequestStatus.AWAITING_CLARIFICATION, RequestStatus.AWAITING_CONFIRMATION}


def generate_reference(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"PAY-{current:%Y%m%d}-{suffix}"


def ensure_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def validate_dates(pay_by: datetime | None, expires_at: datetime, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    expiry = ensure_aware(expires_at)
    if expiry <= current:
        raise AppError("PAYMENT_REQUEST_INVALID", "The payment request contains invalid data.", details=[{"field": "expires_at", "message": "Expiration must be in the future."}])
    if pay_by:
        deadline = ensure_aware(pay_by)
        if deadline <= current:
            raise AppError("PAYMENT_REQUEST_INVALID", "The payment request contains invalid data.", details=[{"field": "pay_by", "message": "Payment deadline must be in the future."}])
        if expiry < deadline:
            raise AppError("PAYMENT_REQUEST_INVALID", "The payment request contains invalid data.", details=[{"field": "expires_at", "message": "Expiration cannot precede the payment deadline."}])


class PaymentRequestService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def create_from_draft(self, conversation_id: str, draft: ExtractedPaymentDraft) -> PaymentRequest:
        expires_at = draft.expires_at
        if not expires_at and draft.validity_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=draft.validity_days)
        complete = not draft.missing_fields and expires_at is not None
        request = PaymentRequest(
            reference_id=generate_reference(datetime.now(ZoneInfo(self.settings.app_timezone))), conversation_id=conversation_id,
            customer_name=draft.customer.name, customer_email=str(draft.customer.email) if draft.customer.email else None,
            customer_phone=draft.customer.phone, currency=(draft.currency or "INR").upper(),
            discount_minor=draft.discount_minor or 0, tax_minor=draft.tax_minor or 0,
            description=draft.description, pay_by=draft.pay_by, expires_at=expires_at,
            status=RequestStatus.AWAITING_CONFIRMATION if complete else RequestStatus.AWAITING_CLARIFICATION,
        )
        self.db.add(request)
        for item in draft.items:
            if item.name and item.quantity and item.unit_price_minor:
                request.items.append(PaymentItem(name=item.name, quantity=item.quantity, unit_price_minor=item.unit_price_minor, line_total_minor=item.quantity * item.unit_price_minor))
        self._recalculate_partial(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def merge_draft(self, request: PaymentRequest, draft: ExtractedPaymentDraft) -> PaymentRequest:
        if request.status not in EDITABLE:
            raise AppError("INVALID_STATUS_TRANSITION", "This request can no longer be edited.", 409)
        if draft.customer.name:
            request.customer_name = draft.customer.name
        if draft.customer.email:
            request.customer_email = str(draft.customer.email)
        if draft.customer.phone:
            request.customer_phone = draft.customer.phone
        if draft.currency:
            request.currency = draft.currency.upper()
        if draft.pay_by:
            request.pay_by = draft.pay_by
        if draft.expires_at:
            request.expires_at = draft.expires_at
        elif draft.validity_days:
            request.expires_at = datetime.now(timezone.utc) + timedelta(days=draft.validity_days)
        if draft.description:
            request.description = draft.description
        if draft.items:
            complete_new = [item for item in draft.items if item.name and item.quantity and item.unit_price_minor]
            if complete_new:
                request.items.clear()
                for item in complete_new:
                    request.items.append(PaymentItem(name=item.name or "", quantity=item.quantity or 1, unit_price_minor=item.unit_price_minor or 0, line_total_minor=(item.quantity or 1) * (item.unit_price_minor or 0)))
        self._recalculate_partial(request)
        request.status = RequestStatus.AWAITING_CONFIRMATION if request.items and request.expires_at else RequestStatus.AWAITING_CLARIFICATION
        self.db.commit()
        self.db.refresh(request)
        return request

    def update(self, request: PaymentRequest, data: PaymentRequestUpdate) -> PaymentRequest:
        if request.status not in EDITABLE:
            raise AppError("INVALID_STATUS_TRANSITION", "This request can no longer be edited.", 409)
        currency = data.currency.upper()
        if currency not in self.settings.supported_currencies:
            raise AppError("UNSUPPORTED_CURRENCY", f"Currency {currency} is not supported.")
        validate_dates(data.pay_by, data.expires_at)
        totals = calculate_totals(data.items, data.discount_minor, data.tax_minor)
        request.customer_name, request.customer_email, request.customer_phone = data.customer.name, str(data.customer.email) if data.customer.email else None, data.customer.phone
        request.currency, request.discount_minor, request.tax_minor = currency, totals.discount, totals.tax
        request.subtotal_minor, request.total_minor = totals.subtotal, totals.total
        request.pay_by, request.expires_at, request.description = data.pay_by, data.expires_at, data.description
        request.items.clear()
        for item, line_total in zip(data.items, totals.line_totals, strict=True):
            request.items.append(PaymentItem(name=item.name, quantity=item.quantity, unit_price_minor=item.unit_price_minor, line_total_minor=line_total))
        request.status = RequestStatus.AWAITING_CONFIRMATION
        self.db.commit()
        self.db.refresh(request)
        return request

    async def confirm(self, request: PaymentRequest, idempotency_key: str, provider: PaymentProvider) -> PaymentRequest:
        if not (8 <= len(idempotency_key) <= 128) or not all(char.isalnum() or char in "-_.:" for char in idempotency_key):
            raise AppError("INVALID_IDEMPOTENCY_KEY", "Idempotency-Key must be 8-128 safe characters.")
        request_hash = self._request_hash(request)
        existing = self.db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key))
        if existing:
            if existing.request_hash != request_hash:
                raise AppError("IDEMPOTENCY_CONFLICT", "This idempotency key was used for a different request.", 409)
            stored = self.db.get(PaymentRequest, existing.resource_id)
            if not stored:
                raise AppError("RESOURCE_NOT_FOUND", "Stored payment request was not found.", 404)
            return stored
        if request.status == RequestStatus.ACTIVE and request.link:
            return request
        if request.status != RequestStatus.AWAITING_CONFIRMATION:
            raise AppError("INVALID_STATUS_TRANSITION", "Only a confirmed draft can create a payment link.", 409)
        if not request.expires_at:
            raise AppError("PAYMENT_REQUEST_INVALID", "Expiration is required.")
        validate_dates(request.pay_by, request.expires_at)
        transitioned = self.db.execute(update(PaymentRequest).where(PaymentRequest.id == request.id, PaymentRequest.status == RequestStatus.AWAITING_CONFIRMATION).values(status=RequestStatus.CREATING)).rowcount
        self.db.commit()
        if transitioned != 1:
            raise AppError("PAYMENT_CREATION_IN_PROGRESS", "Payment-link creation is already in progress.", 409)
        try:
            created = await provider.create_payment_link(request.reference_id, request.total_minor, request.currency, ensure_aware(request.expires_at))
            request = self.db.get(PaymentRequest, request.id) or request
            request.link = PaymentLink(provider=created.provider, provider_link_id=created.provider_link_id, public_token=created.public_token, payment_url=created.payment_url, status=created.status, expires_at=created.expires_at, provider_response_json=json.dumps(created.sanitized_response))
            request.status = RequestStatus.ACTIVE
            request.confirmed_at = datetime.now(timezone.utc)
            self.db.flush()
            response_json = PaymentRequestOut.model_validate(request).model_dump_json()
            self.db.add(IdempotencyRecord(idempotency_key=idempotency_key, operation="confirm_payment_request", request_hash=request_hash, resource_type="payment_request", resource_id=request.id, response_status_code=200, response_json=response_json))
            self.db.commit()
            self.db.refresh(request)
            return request
        except (AppError, IntegrityError) as exc:
            self.db.rollback()
            failed = self.db.get(PaymentRequest, request.id)
            if failed and failed.status == RequestStatus.CREATING:
                failed.status = RequestStatus.AWAITING_CONFIRMATION
                failed.failure_code = "PAYMENT_PROVIDER_FAILED"
                failed.failure_message = "The payment provider could not create a link."
                self.db.commit()
            if isinstance(exc, AppError):
                raise
            raise AppError("PAYMENT_CREATION_CONFLICT", "The payment link could not be created safely.", 409) from exc

    def cancel(self, request: PaymentRequest) -> PaymentRequest:
        self._refresh_expiration(request)
        if request.status != RequestStatus.ACTIVE or not request.link:
            raise AppError("INVALID_STATUS_TRANSITION", "Only active payment links can be cancelled.", 409)
        now = datetime.now(timezone.utc)
        request.status = RequestStatus.CANCELLED
        request.link.status = "CANCELLED"
        request.link.cancelled_at = now
        self.db.commit()
        return request

    def complete_mock(self, request: PaymentRequest) -> PaymentRequest:
        self._refresh_expiration(request)
        if request.status == RequestStatus.PAID:
            raise AppError("PAYMENT_ALREADY_COMPLETED", "This payment has already been completed.", 409)
        if request.status != RequestStatus.ACTIVE or not request.link or request.link.provider != "mock":
            raise AppError("INVALID_STATUS_TRANSITION", "This payment link cannot be completed.", 409)
        now = datetime.now(timezone.utc)
        request.status = RequestStatus.PAID
        request.link.status = "PAID"
        request.link.paid_at = now
        self.db.commit()
        return request

    def _refresh_expiration(self, request: PaymentRequest) -> None:
        if request.status == RequestStatus.ACTIVE and request.expires_at and ensure_aware(request.expires_at) <= datetime.now(timezone.utc):
            request.status = RequestStatus.EXPIRED
            if request.link:
                request.link.status = "EXPIRED"
            self.db.commit()

    def _recalculate_partial(self, request: PaymentRequest) -> None:
        request.subtotal_minor = sum(item.line_total_minor for item in request.items)
        request.total_minor = request.subtotal_minor - request.discount_minor + request.tax_minor

    @staticmethod
    def _request_hash(request: PaymentRequest) -> str:
        payload = {"id": request.id, "currency": request.currency, "items": [(item.name, item.quantity, item.unit_price_minor) for item in request.items], "discount": request.discount_minor, "tax": request.tax_minor, "expires_at": request.expires_at.isoformat() if request.expires_at else None}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
