import re
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator

NAME_MAX = 80
PHONE_MAX = 20
EMAIL_MAX = 120
REASON_MAX = 300
ORDER_MAX = 64
MERCHANT_MAX = 64

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_PHONE_RE = re.compile(r"^\+?\d[\d\s\-]{7,18}$")


class EventCreate(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=MERCHANT_MAX)
    order_id: str = Field(min_length=1, max_length=ORDER_MAX)
    amount: float = Field(gt=0, le=10000000)
    currency: str = "INR"
    status: Literal["failed", "abandoned", "captured"] = "failed"
    failure_reason_code: Optional[str] = Field(default=None, max_length=64)
    failure_reason_text: Optional[str] = Field(default=None, max_length=REASON_MAX)
    customer_name: str = Field(min_length=1, max_length=NAME_MAX)
    customer_phone: str = Field(default="", max_length=PHONE_MAX)
    customer_email: str = Field(default="", max_length=EMAIL_MAX)
    customer_opted_out: bool = False

    @field_validator("customer_phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if v and not _PHONE_RE.match(v):
            raise ValueError("invalid phone number")
        return v

    @field_validator("customer_email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip()
        if v and not _EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v

    @field_validator("customer_name", "merchant_id", "order_id",
                     "failure_reason_code", "failure_reason_text")
    @classmethod
    def sanitize(cls, v: str) -> str:
        return "".join(ch for ch in v if ord(ch) >= 32 or ch in "\t").strip()


def mask_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) <= 4:
        return "*" * len(digits)
    head = digits[:2]
    tail = digits[-2:]
    return f"+{head}*****{tail}"


def mask_email(value: Optional[str]) -> Optional[str]:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


class BatchSummary(BaseModel):
    total_events: int
    total_at_risk: float
    total_recovered: float
    recovery_rate_pct: float
    exception_count: int
    rule_vs_llm_ratio: dict[str, int]
    by_bucket: dict[str, int]
    by_action: dict[str, int]


class DriftReport(BaseModel):
    window_events: int
    threshold_pct: float
    sufficient_data: bool
    flag_raised: bool
    bucket_shifts: dict[str, float]
    recent_recovery_rate_pct: Optional[float]
    baseline_recovery_rate_pct: Optional[float]


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
    customer_phone: Optional[str]
    customer_email: Optional[str]
    customer_opted_out: bool
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


class PendingActionOut(BaseModel):
    decision_id: int
    event_id: int
    order_id: str
    customer_name: str
    amount: float
    bucket: str
    action: str
    rule_fired: str
    created_at: datetime