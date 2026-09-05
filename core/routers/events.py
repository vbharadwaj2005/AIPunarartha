import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import Session, select

from core.config import get_settings
from core.db import get_session
from core.schemas import EventCreate
from core.services.action_executor import execute_recovery
from core.services.classifier import resolve_bucket_by_rule
from core.services.decision_engine import evaluate_decision, build_order_history
from core.services.rate_limit import limiter
from core.services.sarvam_client import classify_free_text
from models import PaymentEvent, Classification, RecoveryDecision, AuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


def _verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _clean(value, max_len: int):
    if value is None:
        return None
    cleaned = "".join(ch for ch in str(value) if ord(ch) >= 32 or ch in "\t").strip()
    return cleaned[:max_len] or None


def _enforce_amount_positive(amount: float):
    if amount <= 0 or amount > 10000000:
        raise HTTPException(status_code=400, detail="amount must be a positive value")


def _recent_duplicate(session: Session, order_id: str, reason_code: str | None, amount: float) -> PaymentEvent | None:
    """Guards against duplicate webhook deliveries for the same failure."""
    window_start = datetime.now(timezone.utc).replace(tzinfo=None)
    matches = session.exec(
        select(PaymentEvent).where(PaymentEvent.order_id == order_id)
    ).all()
    for event in matches:
        if event.status != "failed":
            continue
        if reason_code and event.failure_reason_code != reason_code:
            continue
        if abs(event.amount - amount) > 0.51:
            continue
        if (window_start - event.created_at).total_seconds() < 600:
            return event
    return None


def _ingest_event(session: Session, data: dict, source: str) -> PaymentEvent:
    amount = float(data["amount"])
    _enforce_amount_positive(amount)

    event = PaymentEvent(
        merchant_id=data["merchant_id"],
        order_id=data["order_id"],
        amount=amount,
        currency=data.get("currency", "INR") or "INR",
        status=data.get("status", "failed"),
        failure_reason_code=_clean(data.get("failure_reason_code"), 64),
        failure_reason_text=_clean(data.get("failure_reason_text"), 300),
        customer_name=data["customer_name"] or "Customer",
        customer_phone=data.get("customer_phone", "") or "",
        customer_email=data.get("customer_email", "") or "",
        customer_opted_out=bool(data.get("customer_opted_out", False)),
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    session.add(AuditLog(
        entity_type="PaymentEvent", entity_id=event.id,
        actor="system", action="ingested", detail=f"source: {source}",
    ))
    session.commit()
    return event


async def _classify_and_decide(session: Session, event: PaymentEvent) -> dict:
    """Full pipeline for one event: classify, decide, then (optionally) act."""
    code = event.failure_reason_code
    text = event.failure_reason_text
    bucket, reasoning = resolve_bucket_by_rule(code, text)

    if bucket is None:
        llm_result = await classify_free_text(text or code or "unknown failure")
        bucket = llm_result.bucket
        reasoning = f"[llm] {llm_result.reasoning} (conf={llm_result.confidence:.2f})"
        method = "llm"
        confidence = llm_result.confidence
    else:
        method = "rule"
        confidence = 1.0

    classification = Classification(
        payment_event_id=event.id,
        bucket=bucket, method=method,
        confidence=confidence, reasoning_text=reasoning,
    )
    session.add(classification)
    session.commit()
    session.refresh(classification)

    session.add(AuditLog(
        entity_type="Classification", entity_id=classification.id,
        actor=method, action="classified", detail=reasoning,
    ))
    session.commit()

    prior = build_order_history(session, event)

    action, rule_fired, stopping = evaluate_decision(event, classification, list(prior))

    decision = RecoveryDecision(
        payment_event_id=event.id,
        classification_id=classification.id,
        action=action,
        stopping_rule_triggered=stopping,
        rule_fired=rule_fired,
        created_at=datetime.now(timezone.utc),
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)

    executed = False
    if action != "no_action":
        if get_settings().auto_execute:
            executed = (await execute_recovery(session, event, decision)) is not None
        else:
            session.add(AuditLog(
                entity_type="RecoveryDecision", entity_id=decision.id,
                actor="system", action="pending_review",
                detail="auto-execute is off; awaiting human approval",
            ))
            session.commit()

    return {
        "event_id": event.id,
        "bucket": bucket,
        "method": method,
        "action": action,
        "stopping_rule": stopping,
        "action_executed": executed,
        "awaiting_review": action != "no_action" and not get_settings().auto_execute,
    }


@router.post("/manual", status_code=status.HTTP_201_CREATED)
async def ingest_manual_event(
    payload: EventCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    data = payload.model_dump()
    event = _ingest_event(session, data, "manual")
    return await _classify_and_decide(session, event)


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    body = await request.body()

    if settings.razorpay_webhook_secret:
        if not x_razorpay_signature:
            raise HTTPException(status_code=400, detail="missing webhook signature")
        if not _verify_webhook_signature(body, x_razorpay_signature, settings.razorpay_webhook_secret):
            raise HTTPException(status_code=400, detail="invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json")

    event_type = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if not payment_entity:
        return {"status": "ignored", "event": event_type}

    if "failed" not in event_type:
        return {"status": "ignored", "event": event_type}

    notes = payment_entity.get("notes", {})

    amount_paise = payment_entity.get("amount", 0)
    amount_rupees = float(amount_paise) / 100
    _enforce_amount_positive(amount_rupees)

    reason_code = _clean(payment_entity.get("error_code"), 64)
    order_id = _clean(payment_entity.get("order_id"), 64) or ""
    if not order_id:
        raise HTTPException(status_code=400, detail="missing order id")

    existing = _recent_duplicate(session, order_id, reason_code, amount_rupees)
    if existing is not None:
        return {"status": "duplicate_ignored", "event_id": existing.id}

    data = {
        "order_id": order_id,
        "amount": amount_rupees,
        "currency": payment_entity.get("currency", "INR") or "INR",
        "status": "failed" if "failed" in event_type else "captured",
        "failure_reason_code": reason_code,
        "failure_reason_text": _clean(payment_entity.get("error_description"), 300),
        "customer_name": _clean(notes.get("customer_name"), 80) or "Customer",
        "customer_phone": _clean(notes.get("customer_phone"), 20) or "",
        "customer_email": _clean(notes.get("customer_email"), 120) or "",
        "merchant_id": _clean(notes.get("merchant_id"), 64) or "rzp",
    }

    event = _ingest_event(session, data, f"webhook:{event_type}")
    result = await _classify_and_decide(session, event)
    return {"status": "processed", **result}