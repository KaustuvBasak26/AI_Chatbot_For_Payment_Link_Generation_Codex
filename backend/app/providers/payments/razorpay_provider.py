import base64
import hashlib
import hmac
from datetime import datetime

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.payments.base import ProviderLink


class RazorpayPaymentProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise AppError("PROVIDER_NOT_CONFIGURED", "Razorpay credentials are not configured.", 503)
        self.key_id = settings.razorpay_key_id
        self.secret = settings.razorpay_key_secret.get_secret_value()
        self.webhook_secret = settings.razorpay_webhook_secret.get_secret_value() if settings.razorpay_webhook_secret else ""

    async def create_payment_link(self, reference_id: str, amount_minor: int, currency: str, expires_at: datetime) -> ProviderLink:
        auth = base64.b64encode(f"{self.key_id}:{self.secret}".encode()).decode()
        payload = {"amount": amount_minor, "currency": currency, "reference_id": reference_id, "expire_by": int(expires_at.timestamp())}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post("https://api.razorpay.com/v1/payment_links", json=payload, headers={"Authorization": f"Basic {auth}"})
            response.raise_for_status()
            data = response.json()
            return ProviderLink("razorpay", data["id"], data["id"], data["short_url"], "ACTIVE", expires_at, {"id": data["id"], "status": data.get("status", "created")})
        except (httpx.HTTPError, KeyError) as exc:
            raise AppError("PAYMENT_PROVIDER_FAILED", "Razorpay could not create the payment link.", 502) from exc

    async def verify_webhook_signature(self, body: bytes, signature: str | None) -> bool:
        if not signature or not self.webhook_secret:
            return False
        expected = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

