import secrets
import string
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.payments.base import ProviderLink


def generate_public_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class MockPaymentProvider:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.mock_payment_base_url.rstrip("/")

    async def create_payment_link(self, reference_id: str, amount_minor: int, currency: str, expires_at: datetime) -> ProviderLink:
        if expires_at <= datetime.now(timezone.utc):
            raise AppError("PAYMENT_REQUEST_INVALID", "Expiration must be in the future.")
        token = generate_public_token()
        provider_id = f"mock_{generate_public_token(20)}"
        return ProviderLink("mock", provider_id, token, f"{self.base_url}/{token}", "ACTIVE", expires_at, {"id": provider_id, "status": "ACTIVE"})

    async def verify_webhook_signature(self, body: bytes, signature: str | None) -> bool:
        return False

