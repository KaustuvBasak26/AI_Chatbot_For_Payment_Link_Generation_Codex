from app.core.config import Settings


def test_supported_currencies_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("SUPPORTED_CURRENCIES", "INR, usd")

    settings = Settings(_env_file=None)

    assert settings.supported_currencies == ("INR", "USD")
