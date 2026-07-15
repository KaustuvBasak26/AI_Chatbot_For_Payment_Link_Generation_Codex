import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    messages: Mapped[list["ConversationMessage"]] = relationship(cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    __table_args__ = (
        Index("ix_payment_requests_status", "status"),
        Index("ix_payment_requests_customer_email", "customer_email"),
        Index("ix_payment_requests_created_at", "created_at"),
        Index("ix_payment_requests_expires_at", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200))
    customer_email: Mapped[str | None] = mapped_column(String(320))
    customer_phone: Mapped[str | None] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    subtotal_minor: Mapped[int] = mapped_column(Integer, default=0)
    discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(String(1000))
    pay_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(80))
    failure_message: Mapped[str | None] = mapped_column(String(500))
    items: Mapped[list["PaymentItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    link: Mapped["PaymentLink | None"] = relationship(back_populates="payment_request", lazy="selectin")


class PaymentItem(Base):
    __tablename__ = "payment_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_request_id: Mapped[str] = mapped_column(ForeignKey("payment_requests.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor: Mapped[int] = mapped_column(Integer)
    line_total_minor: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaymentLink(Base):
    __tablename__ = "payment_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_request_id: Mapped[str] = mapped_column(ForeignKey("payment_requests.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_link_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    public_token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    payment_url: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    provider_response_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_request: Mapped[PaymentRequest] = relationship(back_populates="link")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    operation: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(36))
    response_status_code: Mapped[int] = mapped_column(Integer)
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

