from fastapi import APIRouter, Header, Request

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.providers.payments.razorpay_provider import RazorpayPaymentProvider

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{provider}", status_code=202)
async def webhook(provider: str, request: Request, x_razorpay_signature: str | None = Header(default=None)) -> dict[str, bool]:
    if provider != "razorpay":
        raise AppError("WEBHOOK_PROVIDER_UNSUPPORTED", "Webhook provider is unsupported.", 404)
    body = await request.body()
    adapter = RazorpayPaymentProvider(get_settings())
    if not await adapter.verify_webhook_signature(body, x_razorpay_signature):
        raise AppError("WEBHOOK_SIGNATURE_INVALID", "Webhook signature is invalid.", 401)
    return {"accepted": True}

