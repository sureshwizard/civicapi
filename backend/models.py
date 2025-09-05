from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
import uuid

class BillIn(BaseModel):
    vendor: str
    amount: float
    due_date: date
    note: Optional[str] = None

class Bill(BillIn):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "unpaid"  # unpaid | paid | canceled

class NotifyIn(BaseModel):
    bill_id: str
    channel: str = "auto"  # auto|sms|email|console
    to: Optional[str] = None  # phone/email for demo

