from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    ContentFilterFinishReasonError,
    InternalServerError,
    LengthFinishReasonError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from pydantic import SecretStr, ValidationError

from app.core.exceptions import AppError
from app.schemas.payment import ExtractedPaymentDraft
from app.services.deterministic_extractor import required_missing_fields

INSTRUCTION = """You extract structured payment-request information from vendor messages.

Return only information supported by the user's message and recent conversation context.
Do not invent customer information, items, quantities, prices, currencies, dates, discounts,
taxes, payment deadlines, or validity periods. Extract every item separately. Represent money
in the currency's smallest unit. Do not calculate line totals, subtotal, taxable amount, tax
results, discount results, or final total. Resolve relative dates only from the supplied backend
date and timezone. Record material ambiguity instead of guessing. List required absent fields in
missing_fields. You cannot create payment links, call payment providers, approve transactions,
or modify database records."""


class OpenAIExtractor:
    def __init__(self, api_key: SecretStr, model: str, timeout: float) -> None:
        self.client = AsyncOpenAI(api_key=api_key.get_secret_value(), timeout=timeout, max_retries=0)
        self.model = model

    async def extract_payment_request(
        self, user_message: str, conversation_context: list[dict[str, str]], current_date: str, timezone: str
    ) -> ExtractedPaymentDraft:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=f"{INSTRUCTION}\nBackend current date: {current_date}. Application timezone: {timezone}.",
                input=[*conversation_context, {"role": "user", "content": user_message}],
                text_format=ExtractedPaymentDraft,
                store=False,
            )
            if not response.output_parsed:
                raise AppError("LLM_INVALID_OUTPUT", "OpenAI returned no structured result.", 502)
            result = ExtractedPaymentDraft.model_validate(response.output_parsed)
            result.missing_fields = required_missing_fields(result)
            return result
        except AuthenticationError as exc:
            raise AppError("LLM_AUTHENTICATION_FAILED", "The OpenAI API key could not be authenticated.", 401) from exc
        except PermissionDeniedError as exc:
            raise AppError("LLM_PERMISSION_DENIED", "The OpenAI key cannot use this model.", 403) from exc
        except NotFoundError as exc:
            raise AppError("LLM_MODEL_NOT_FOUND", "The selected OpenAI model was not found or is unavailable to this project.", 404) from exc
        except (BadRequestError, UnprocessableEntityError) as exc:
            raise AppError("LLM_MODEL_UNSUPPORTED", "The selected OpenAI model could not produce structured extraction output.", 400) from exc
        except RateLimitError as exc:
            raise AppError("LLM_RATE_LIMITED", "OpenAI is temporarily rate limited.", 503) from exc
        except (APITimeoutError, APIConnectionError, InternalServerError) as exc:
            raise AppError("LLM_TEMPORARILY_UNAVAILABLE", "OpenAI is temporarily unavailable.", 503) from exc
        except LengthFinishReasonError as exc:
            raise AppError("LLM_INVALID_OUTPUT", "OpenAI could not finish the structured extraction.", 502) from exc
        except ContentFilterFinishReasonError as exc:
            raise AppError("LLM_OUTPUT_BLOCKED", "OpenAI could not return extraction output for this request.", 422) from exc
        except ValidationError as exc:
            raise AppError("LLM_INVALID_OUTPUT", "OpenAI returned invalid structured data.", 502) from exc
        except APIStatusError as exc:
            raise AppError("LLM_PROVIDER_ERROR", "OpenAI rejected the extraction request.", 502) from exc

    async def test_connection(self) -> None:
        try:
            await self.client.models.retrieve(self.model)
        except AuthenticationError as exc:
            raise AppError("LLM_AUTHENTICATION_FAILED", "The OpenAI API key could not be authenticated.", 401) from exc
        except PermissionDeniedError as exc:
            raise AppError("LLM_PERMISSION_DENIED", "The OpenAI key cannot use this model.", 403) from exc
        except NotFoundError as exc:
            raise AppError("LLM_MODEL_NOT_FOUND", "The selected OpenAI model was not found or is unavailable to this project.", 404) from exc
        except RateLimitError as exc:
            raise AppError("LLM_RATE_LIMITED", "OpenAI is temporarily rate limited.", 503) from exc
        except (APITimeoutError, APIConnectionError, InternalServerError) as exc:
            raise AppError("LLM_TEMPORARILY_UNAVAILABLE", "OpenAI is temporarily unavailable.", 503) from exc
        except APIStatusError as exc:
            raise AppError("LLM_CONNECTION_FAILED", "OpenAI rejected the connection test.", 502) from exc
