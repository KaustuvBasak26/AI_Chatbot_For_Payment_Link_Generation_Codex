from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ProviderLink:
    provider: str
    provider_link_id: str
    public_token: str
    payment_url: str
    status: str
    expires_at: datetime
    sanitized_response: dict[str, str]


class PaymentProvider(Protocol):
    async def create_payment_link(self, reference_id: str, amount_minor: int, currency: str, expires_at: datetime) -> ProviderLink: ...
    async def verify_webhook_signature(self, body: bytes, signature: str | None) -> bool: ...

