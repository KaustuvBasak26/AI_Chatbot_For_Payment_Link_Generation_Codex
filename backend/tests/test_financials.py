from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import AppError
from app.schemas.payment import PaymentItemUpdate
from app.services.payment_calculator import calculate_totals
from app.services.payment_request_service import generate_reference, validate_dates


def test_authoritative_totals() -> None:
    items = [PaymentItemUpdate(name="Chair", quantity=2, unit_price_minor=450000), PaymentItemUpdate(name="Desk", quantity=1, unit_price_minor=800000)]
    totals = calculate_totals(items, discount_minor=100000, tax_minor=180000)
    assert totals.line_totals == [900000, 800000]
    assert totals.subtotal == 1700000
    assert totals.total == 1780000


def test_discount_cannot_exceed_subtotal() -> None:
    with pytest.raises(AppError, match="invalid data"):
        calculate_totals([PaymentItemUpdate(name="Item", quantity=1, unit_price_minor=100)], 101, 0)


def test_dates_validate_deadline_order() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(AppError):
        validate_dates(now + timedelta(days=2), now + timedelta(days=1), now)
    with pytest.raises(AppError):
        validate_dates(None, now - timedelta(seconds=1), now)


def test_reference_format_and_uniqueness() -> None:
    first, second = generate_reference(), generate_reference()
    assert first.startswith("PAY-") and len(first) == 19
    assert first != second

