import logging

from app.core.logging import SecretRedactionFilter
from app.providers.payments.mock_provider import generate_public_token


def test_secret_redaction() -> None:
    value = SecretRedactionFilter.redact("X-LLM-API-Key: sk-supersecret123456 Authorization=Bearer-token")
    assert "sk-supersecret" not in value
    assert "Bearer-token" not in value


def test_mock_tokens_are_secure_and_unique() -> None:
    first, second = generate_public_token(), generate_public_token()
    assert len(first) == 32 and first != second

