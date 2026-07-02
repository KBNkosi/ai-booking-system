import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.booking_request import BookingRequest

class BookingRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, booking_request: BookingRequest) -> BookingRequest:
        self.db.add(booking_request)
        self.db.flush()
        self.db.refresh(booking_request)
        return booking_request

    def get_by_id(self, request_id: uuid.UUID) -> Optional[BookingRequest]:
        booking_request = self.db.get(BookingRequest, request_id)
        if not booking_request:
            return None
        return booking_request

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[BookingRequest]:
        stmt = (
            select(BookingRequest)
            .where(BookingRequest.idempotency_key == idempotency_key)
        )
        return self.db.scalars(stmt).first()

    def update_status(self, request_id: uuid.UUID, status: str) -> Optional[BookingRequest]:
        booking_request = self.db.get(BookingRequest, request_id)
        if not booking_request:
            return None
        booking_request.status = status
        self.db.flush()
        return booking_request


    
    