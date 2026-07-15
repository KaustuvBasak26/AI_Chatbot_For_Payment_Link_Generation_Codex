from datetime import datetime

import pytest

from app.services.deterministic_extractor import DeterministicExtractor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("3 keyboards at ₹2,000 each valid for 7 days", [("keyboards", 3, 200000)]),
        ("two office chairs costing 4500 each", [("office chairs", 2, 450000)]),
        ("1 desk for INR 8000 expires on 22 July 2026", [("desk", 1, 800000)]),
        ("five software licences at Rs. 1,200 each", [("software licences", 5, 120000)]),
    ],
)
async def test_representative_item_extraction(prompt: str, expected: list[tuple[str, int, int]]) -> None:
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert [(item.name, item.quantity, item.unit_price_minor) for item in draft.items] == expected


@pytest.mark.asyncio
async def test_multiple_items_customer_and_dates() -> None:
    prompt = "Charge Rahul Sharma for two office chairs at INR 4,500 each and one desk at INR 8,000. His email is rahul@example.com. Payment is due on 20 July 2026 and the link expires on 22 July 2026."
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert draft.customer.name == "Rahul Sharma"
    assert str(draft.customer.email) == "rahul@example.com"
    assert len(draft.items) == 2
    assert draft.pay_by and draft.pay_by.day == 20
    assert draft.expires_at and draft.expires_at.day == 22


@pytest.mark.asyncio
async def test_relative_friday_and_missing_expiry() -> None:
    draft = await DeterministicExtractor().extract_payment_request("3 keyboards at ₹2,000 each, due by Friday", [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert draft.pay_by and draft.pay_by.weekday() == 4
    assert "expiration" in draft.missing_fields


@pytest.mark.asyncio
async def test_natural_variants_lakh_and_number_words() -> None:
    prompt = "Bill Anita for 3 x ergonomic chairs @ 4,500 each and two desks costing Rs 8,000 each. Keep it active for ten days."
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert draft.customer.name == "Anita"
    assert [(item.name, item.quantity, item.unit_price_minor) for item in draft.items] == [
        ("ergonomic chairs", 3, 450000),
        ("desks", 2, 800000),
    ]
    assert draft.validity_days == 10


@pytest.mark.asyncio
async def test_price_first_labelled_item_and_adjustments() -> None:
    prompt = "Office chairs, quantity 4, unit price INR 3,250; discount ₹500 and GST ₹900. Valid until 30 July 2026."
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert [(item.name, item.quantity, item.unit_price_minor) for item in draft.items] == [("Office chairs", 4, 325000)]
    assert draft.discount_minor == 50000
    assert draft.tax_minor == 90000
    assert draft.expires_at and draft.expires_at.day == 30


@pytest.mark.asyncio
async def test_partial_service_asks_for_quantity_without_inventing_it() -> None:
    prompt = "Create a request for website design costing ₹25,000 and expires in 5 days."
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert draft.items[0].name == "website design"
    assert draft.items[0].quantity is None
    assert draft.items[0].unit_price_minor == 2500000
    assert draft.missing_fields == ["items.0.quantity"]


@pytest.mark.asyncio
async def test_bare_k_price_each_and_tomorrow() -> None:
    prompt = "Send a payment request for 2 monitors at 15k each, payable tomorrow, valid for 7 days."
    draft = await DeterministicExtractor().extract_payment_request(prompt, [], "2026-07-15T10:00:00+05:30", "Asia/Kolkata")
    assert [(item.name, item.quantity, item.unit_price_minor) for item in draft.items] == [("monitors", 2, 1500000)]
    assert draft.pay_by and draft.pay_by.day == 16
