from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import RequestStatus


class CustomerDraft(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class ItemDraft(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    quantity: int | None = Field(default=None, ge=1, le=100000)
    unit_price_minor: int | None = Field(default=None, ge=1, le=1_000_000_000)


class ExtractedPaymentDraft(BaseModel):
    customer: CustomerDraft = Field(default_factory=CustomerDraft)
    items: list[ItemDraft] = Field(default_factory=list)
    currency: str | None = Field(default=None, max_length=3)
    discount_minor: int | None = Field(default=0, ge=0)
    tax_minor: int | None = Field(default=0, ge=0)
    pay_by: datetime | None = None
    expires_at: datetime | None = None
    validity_days: int | None = Field(default=None, ge=1, le=365)
    description: str | None = Field(default=None, max_length=1000)
    missing_fields: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class PaymentItemUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    quantity: int = Field(ge=1, le=100000)
    unit_price_minor: int = Field(ge=1, le=1_000_000_000)


class PaymentRequestUpdate(BaseModel):
    customer: CustomerDraft = Field(default_factory=CustomerDraft)
    items: list[PaymentItemUpdate] = Field(min_length=1, max_length=100)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    discount_minor: int = Field(default=0, ge=0)
    tax_minor: int = Field(default=0, ge=0)
    pay_by: datetime | None = None
    expires_at: datetime
    description: str | None = Field(default=None, max_length=1000)


class PaymentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class PaymentLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    provider: str
    provider_link_id: str | None
    public_token: str
    payment_url: str
    status: str
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None


class PaymentRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    reference_id: str
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    currency: str
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    total_minor: int
    description: str | None
    pay_by: datetime | None
    expires_at: datetime | None
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    items: list[PaymentItemOut]
    link: PaymentLinkOut | None

