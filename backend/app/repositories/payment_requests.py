from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import PaymentRequest, RequestStatus


class PaymentRequestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, request_id: str) -> PaymentRequest | None:
        return self.db.get(PaymentRequest, request_id)

    def list(self, page: int, page_size: int, status: RequestStatus | None, search: str | None, descending: bool) -> tuple[list[PaymentRequest], int]:
        query: Select[tuple[PaymentRequest]] = select(PaymentRequest)
        if status:
            query = query.where(PaymentRequest.status == status)
        if search:
            term = f"%{search}%"
            query = query.where(or_(PaymentRequest.reference_id.ilike(term), PaymentRequest.customer_email.ilike(term), PaymentRequest.customer_name.ilike(term)))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        order = PaymentRequest.created_at.desc() if descending else PaymentRequest.created_at.asc()
        rows = self.db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
        return list(rows), total

