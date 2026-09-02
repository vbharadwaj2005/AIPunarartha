from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventCreate(BaseModel):
    merchant_id: str
    order_id: str
    amount: float
    currency: str = "INR"
    status: str = "failed"
    failure_reason_code: Optional[str] = None
    failure_reason_text: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_email: str


class BatchSummary(BaseModel):
    total_events: int
    total_at_risk: float
    total_recovered: float
    recovery_rate_pct: float
    exception_count: int
    rule_vs_llm_ratio: dict[str, int]
    by_bucket: dict[str, int]
    by_action: dict[str, int]


class RecordOut(BaseModel):
    id: int
    merchant_id: str
    order_id: str
    amount: float
    currency: str
    status: str
    failure_reason_code: Optional[str]
    failure_reason_text: Optional[str]
    customer_name: str
    customer_phone: str
    customer_email: str
    created_at: datetime
    classification_bucket: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None
    decision_action: Optional[str] = None
    decision_stopping_rule: Optional[str] = None
    decision_rule_fired: Optional[str] = None
    action_channel: Optional[str] = None
    action_message: Optional[str] = None
    action_language: Optional[str] = None
    action_payment_link: Optional[str] = None
    action_outcome: Optional[str] = None


class ExceptionRecord(BaseModel):
    event_id: int
    order_id: str
    customer_name: str
    amount: float
    bucket: str
    stopping_rule: str
    rule_fired: str
    detail: str
