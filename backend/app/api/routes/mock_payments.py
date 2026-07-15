from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models import PaymentLink
from app.db.session import get_db
from app.schemas.payment import PaymentRequestOut
from app.services.payment_request_service import PaymentRequestService

router = APIRouter(prefix="/mock/payment-links", tags=["mock payments"])


def find_by_token(db: Session, token: str):
    link = db.scalar(select(PaymentLink).where(PaymentLink.public_token == token, PaymentLink.provider == "mock"))
    if not link:
        raise AppError("PAYMENT_LINK_NOT_FOUND", "Payment link was not found.", 404)
    return link.payment_request


@router.get("/{public_token}", response_model=PaymentRequestOut)
def mock_details(public_token: str, db: Session = Depends(get_db)):
    request = find_by_token(db, public_token)
    PaymentRequestService(db, get_settings())._refresh_expiration(request)
    return request


@router.post("/{public_token}/complete", response_model=PaymentRequestOut)
def complete_mock(public_token: str, db: Session = Depends(get_db)):
    return PaymentRequestService(db, get_settings()).complete_mock(find_by_token(db, public_token))

