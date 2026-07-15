from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models import RequestStatus
from app.db.session import get_db
from app.providers.payments.mock_provider import MockPaymentProvider
from app.providers.payments.razorpay_provider import RazorpayPaymentProvider
from app.repositories.payment_requests import PaymentRequestRepository
from app.schemas.payment import PaymentRequestOut, PaymentRequestUpdate
from app.services.payment_request_service import PaymentRequestService

router = APIRouter(prefix="/payment-requests", tags=["payment requests"])


class PaymentList(BaseModel):
    items: list[PaymentRequestOut]
    total: int
    page: int
    page_size: int


def find_or_404(db: Session, request_id: str):
    request = PaymentRequestRepository(db).get(request_id)
    if not request:
        raise AppError("PAYMENT_REQUEST_NOT_FOUND", "Payment request was not found.", 404)
    PaymentRequestService(db, get_settings())._refresh_expiration(request)
    return request


@router.get("", response_model=PaymentList)
def list_requests(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: RequestStatus | None = None, search: str | None = Query(None, max_length=200), sort: str = Query("desc", pattern="^(asc|desc)$"), db: Session = Depends(get_db)) -> PaymentList:
    rows, total = PaymentRequestRepository(db).list(page, page_size, status, search, sort == "desc")
    return PaymentList(items=[PaymentRequestOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size)


@router.get("/{request_id}", response_model=PaymentRequestOut)
def get_request(request_id: str, db: Session = Depends(get_db)):
    return find_or_404(db, request_id)


@router.patch("/{request_id}", response_model=PaymentRequestOut)
def update_request(request_id: str, data: PaymentRequestUpdate, db: Session = Depends(get_db)):
    return PaymentRequestService(db, get_settings()).update(find_or_404(db, request_id), data)


@router.post("/{request_id}/confirm", response_model=PaymentRequestOut)
async def confirm_request(request_id: str, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")], db: Session = Depends(get_db)):
    settings = get_settings()
    provider = MockPaymentProvider(settings) if settings.payment_provider == "mock" else RazorpayPaymentProvider(settings)
    return await PaymentRequestService(db, settings).confirm(find_or_404(db, request_id), idempotency_key, provider)


@router.post("/{request_id}/cancel", response_model=PaymentRequestOut)
def cancel_request(request_id: str, db: Session = Depends(get_db)):
    return PaymentRequestService(db, get_settings()).cancel(find_or_404(db, request_id))

