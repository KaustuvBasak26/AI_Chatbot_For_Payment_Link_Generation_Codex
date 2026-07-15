from dataclasses import dataclass

from app.core.exceptions import AppError
from app.schemas.payment import PaymentItemUpdate


@dataclass(frozen=True)
class Totals:
    line_totals: list[int]
    subtotal: int
    discount: int
    tax: int
    total: int


def calculate_totals(items: list[PaymentItemUpdate], discount_minor: int = 0, tax_minor: int = 0) -> Totals:
    if not items:
        raise AppError("PAYMENT_REQUEST_INVALID", "At least one item is required.")
    line_totals = [item.quantity * item.unit_price_minor for item in items]
    subtotal = sum(line_totals)
    if discount_minor > subtotal:
        raise AppError(
            "PAYMENT_REQUEST_INVALID",
            "The payment request contains invalid data.",
            details=[{"field": "discount_minor", "message": "Discount cannot exceed subtotal."}],
        )
    total = subtotal - discount_minor + tax_minor
    if total <= 0 or total > 10_000_000_000_000:
        raise AppError("PAYMENT_REQUEST_INVALID", "The final total is invalid.")
    return Totals(line_totals, subtotal, discount_minor, tax_minor, total)

