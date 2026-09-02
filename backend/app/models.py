from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def _utcnow():
    return datetime.now(timezone.utc)


class PaymentEvent(SQLModel, table=True):
    __tablename__ = "payment_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: str = Field(index=True)
    order_id: str = Field(index=True)
    amount: float
    currency: str = "INR"
    status: str  # failed | abandoned | captured
    failure_reason_code: Optional[str] = None
    failure_reason_text: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_email: str
    created_at: datetime = Field(default_factory=_utcnow)


class Classification(SQLModel, table=True):
    __tablename__ = "classifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    payment_event_id: int = Field(foreign_key="payment_events.id", index=True)
    bucket: str  # insufficient_funds | card_expired | bank_timeout | 3ds_failed | generic_decline | ambiguous
    method: str  # rule | llm
    confidence: Optional[float] = None
    reasoning_text: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class RecoveryDecision(SQLModel, table=True):
    __tablename__ = "recovery_decisions"

    id: Optional[int] = Field(default=None, primary_key=True)
    payment_event_id: int = Field(foreign_key="payment_events.id", index=True)
    classification_id: int = Field(foreign_key="classifications.id")
    action: str  # retry_link | reminder | escalate | no_action
    stopping_rule_triggered: Optional[str] = None
    rule_fired: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class RecoveryAction(SQLModel, table=True):
    __tablename__ = "recovery_actions"

    id: Optional[int] = Field(default=None, primary_key=True)
    recovery_decision_id: int = Field(foreign_key="recovery_decisions.id", index=True)
    channel: str  # sms | email | whatsapp_sim
    message_text: str
    language: str  # en | hi | hi-en
    payment_link_url: Optional[str] = None
    sent_at: datetime = Field(default_factory=_utcnow)
    outcome: Optional[str] = None  # recovered | still_failed | no_response


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str
    entity_id: int
    actor: str  # rule | llm | system
    action: str
    detail: str
    timestamp: datetime = Field(default_factory=_utcnow)
