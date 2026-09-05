import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from ..db import get_session
from ..models import PaymentEvent, Classification, AuditLog
from ..schemas import EventCreate
from ..services.classifier import resolve_bucket_by_rule
from ..services.sarvam_client import classify_free_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


def _verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _ingest_event(session: Session, data: dict) -> PaymentEvent:
    amount = data.get("amount", 0)
    # Razorpay sends amount in paise, convert to rupees
    if isinstance(amount, (int, float)) and amount > 1000:
        amount = amount / 100

    event = PaymentEvent(
        merchant_id=data.get("merchant_id", "unknown"),
        order_id=data.get("order_id", data.get("id", "")),
        amount=float(amount),
        currency=data.get("currency", "INR"),
        status=data.get("status", "failed"),
        failure_reason_code=data.get("failure_reason_code"),
        failure_reason_text=data.get("failure_reason_text"),
        customer_name=data.get("customer_name", "Customer"),
        customer_phone=data.get("customer_phone", ""),
        customer_email=data.get("customer_email", ""),
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    session.add(AuditLog(
        entity_type="PaymentEvent", entity_id=event.id,
        actor="system", action="ingested",
        detail=f"Source: {data.get('_source', 'manual')}",
    ))
    session.commit()
    return event


@router.post("/manual", status_code=status.HTTP_201_CREATED)
def ingest_manual_event(payload: EventCreate, session: Session = Depends(get_session)):
    data = payload.model_dump()
    data["_source"] = "manual"
    return _ingest_event(session, data)


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    session: Session = Depends(get_session),
):
    from ..config import get_settings
    settings = get_settings()

    body = await request.body()

    if settings.razorpay_webhook_secret and x_razorpay_signature:
        if not _verify_webhook_signature(body, x_razorpay_signature, settings.razorpay_webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if not payment_entity:
        return {"status": "ignored", "event": event_type}

    # pull customer info from Razorpay notes if available
    notes = payment_entity.get("notes", {})

    data = {
        "order_id": payment_entity.get("order_id", ""),
        "amount": payment_entity.get("amount", 0),
        "currency": payment_entity.get("currency", "INR"),
        "status": "failed" if "failed" in event_type else "captured",
        "failure_reason_code": payment_entity.get("error_code"),
        "failure_reason_text": payment_entity.get("error_description"),
        "customer_name": notes.get("customer_name", "Customer"),
        "customer_phone": notes.get("customer_phone", ""),
        "customer_email": notes.get("customer_email", ""),
        "merchant_id": notes.get("merchant_id", "rzp"),
        "_source": f"webhook:{event_type}",
    }

    event = _ingest_event(session, data)

    # classify the failure
    code = data["failure_reason_code"]
    text = data["failure_reason_text"]
    bucket, reasoning = resolve_bucket_by_rule(code, text)

    if bucket is None:
        llm_result = await classify_free_text(text or code or "unknown failure")
        bucket = llm_result.bucket
        reasoning = f"[LLM] {llm_result.reasoning} (conf={llm_result.confidence:.2f})"
        method = "llm"
        confidence = llm_result.confidence
    else:
        method = "rule"
        confidence = 1.0

    classification = Classification(
        payment_event_id=event.id,
        bucket=bucket,
        method=method,
        confidence=confidence,
        reasoning_text=reasoning,
    )
    session.add(classification)
    session.commit()

    session.add(AuditLog(
        entity_type="Classification", entity_id=classification.id,
        actor=method, action="classified", detail=reasoning,
    ))
    session.commit()

    return {"status": "processed", "event_id": event.id, "bucket": bucket, "method": method}
