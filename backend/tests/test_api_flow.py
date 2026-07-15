from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


VALID_PROMPT = "Create a payment link for 3 keyboards at ₹2,000 each. Payment is due by 18 July 2026 and the link should remain valid for 7 days."


def chat(client: TestClient, message: str, conversation_id: str | None = None):
    return client.post("/api/v1/chat/messages", json={"conversation_id": conversation_id, "message": message, "use_llm_extraction": False, "allow_deterministic_fallback": True})


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"application": "ok", "database": "ok"}


def test_incomplete_prompt_and_follow_up(client: TestClient) -> None:
    first = chat(client, "Create a payment request for three keyboards.")
    assert first.status_code == 200
    assert first.json()["requires_clarification"] is True
    second = chat(client, "₹2,000 each and valid for 7 days.", first.json()["conversation_id"])
    assert second.status_code == 200, second.text
    assert second.json()["requires_confirmation"] is True
    assert second.json()["draft"]["items"][0]["unit_price_minor"] == 200000


def test_complete_mock_lifecycle_and_idempotency(client: TestClient) -> None:
    created = chat(client, VALID_PROMPT)
    assert created.status_code == 200, created.text
    request_id = created.json()["payment_request_id"]
    detail = client.get(f"/api/v1/payment-requests/{request_id}").json()
    assert detail["subtotal_minor"] == 600000
    confirmed = client.post(f"/api/v1/payment-requests/{request_id}/confirm", headers={"Idempotency-Key": "demo-key-123"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "ACTIVE"
    repeated = client.post(f"/api/v1/payment-requests/{request_id}/confirm", headers={"Idempotency-Key": "demo-key-123"})
    assert repeated.status_code == 200
    assert repeated.json()["link"]["payment_url"] == confirmed.json()["link"]["payment_url"]
    token = confirmed.json()["link"]["public_token"]
    paid = client.post(f"/api/v1/mock/payment-links/{token}/complete")
    assert paid.status_code == 200
    assert paid.json()["status"] == "PAID"
    assert client.post(f"/api/v1/mock/payment-links/{token}/complete").status_code == 409
    history = client.get("/api/v1/payment-requests").json()
    assert history["total"] == 1 and history["items"][0]["status"] == "PAID"


def test_edit_and_cancel(client: TestClient) -> None:
    request_id = chat(client, VALID_PROMPT).json()["payment_request_id"]
    expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    update = client.patch(f"/api/v1/payment-requests/{request_id}", json={
        "customer": {"name": "Asha", "email": "asha@example.com", "phone": None},
        "items": [{"name": "Keyboard", "quantity": 4, "unit_price_minor": 250000}],
        "currency": "INR", "discount_minor": 100000, "tax_minor": 180000,
        "pay_by": None, "expires_at": expiry, "description": "Updated request",
    })
    assert update.status_code == 200, update.text
    assert update.json()["total_minor"] == 1080000
    confirmed = client.post(f"/api/v1/payment-requests/{request_id}/confirm", headers={"Idempotency-Key": "cancel-key-123"})
    assert confirmed.status_code == 200
    cancelled = client.post(f"/api/v1/payment-requests/{request_id}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    assert client.patch(f"/api/v1/payment-requests/{request_id}", json={
        "customer": {}, "items": [{"name": "X", "quantity": 1, "unit_price_minor": 1}], "currency": "INR", "expires_at": expiry
    }).status_code == 409


def test_idempotency_conflict_across_requests(client: TestClient) -> None:
    first_id = chat(client, VALID_PROMPT).json()["payment_request_id"]
    second_id = chat(client, VALID_PROMPT).json()["payment_request_id"]
    assert client.post(f"/api/v1/payment-requests/{first_id}/confirm", headers={"Idempotency-Key": "shared-key-123"}).status_code == 200
    conflict = client.post(f"/api/v1/payment-requests/{second_id}/confirm", headers={"Idempotency-Key": "shared-key-123"})
    assert conflict.status_code == 409


def test_llm_key_never_returned(client: TestClient) -> None:
    response = client.post("/api/v1/chat/messages", headers={"X-LLM-Provider": "openai", "X-LLM-Model": "test-model", "X-LLM-API-Key": "sk-secret-value-123456"}, json={"message": VALID_PROMPT, "use_llm_extraction": False})
    assert "sk-secret" not in response.text

