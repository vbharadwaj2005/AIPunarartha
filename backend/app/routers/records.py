from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import PaymentEvent, Classification, RecoveryDecision, RecoveryAction, AuditLog
from ..schemas import RecordOut, ExceptionRecord

router = APIRouter(prefix="/api/records", tags=["records"])


def _to_record(event, classification, decision, action) -> RecordOut:
    return RecordOut(
        id=event.id,
        merchant_id=event.merchant_id,
        order_id=event.order_id,
        amount=event.amount,
        currency=event.currency,
        status=event.status,
        failure_reason_code=event.failure_reason_code,
        failure_reason_text=event.failure_reason_text,
        customer_name=event.customer_name,
        customer_phone=event.customer_phone,
        customer_email=event.customer_email,
        created_at=event.created_at,
        classification_bucket=classification.bucket if classification else None,
        classification_method=classification.method if classification else None,
        classification_confidence=classification.confidence if classification else None,
        classification_reasoning=classification.reasoning_text if classification else None,
        decision_action=decision.action if decision else None,
        decision_stopping_rule=decision.stopping_rule_triggered if decision else None,
        decision_rule_fired=decision.rule_fired if decision else None,
        action_channel=action.channel if action else None,
        action_message=action.message_text if action else None,
        action_language=action.language if action else None,
        action_payment_link=action.payment_link_url if action else None,
        action_outcome=action.outcome if action else None,
    )


@router.get("/", response_model=list[RecordOut])
def list_records(
    bucket: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    events = session.exec(select(PaymentEvent).offset(skip).limit(limit)).all()
    results = []

    for event in events:
        cls = session.exec(
            select(Classification).where(Classification.payment_event_id == event.id)
        ).first()

        if bucket and cls and cls.bucket != bucket:
            continue

        dec = session.exec(
            select(RecoveryDecision).where(RecoveryDecision.payment_event_id == event.id)
        ).first()

        if action and dec and dec.action != action:
            continue

        act = None
        if dec:
            act = session.exec(
                select(RecoveryAction).where(RecoveryAction.recovery_decision_id == dec.id)
            ).first()

        results.append(_to_record(event, cls, dec, act))

    return results


@router.get("/exceptions/list", response_model=list[ExceptionRecord])
def list_exceptions(session: Session = Depends(get_session)):
    decisions = session.exec(
        select(RecoveryDecision).where(RecoveryDecision.stopping_rule_triggered.is_not(None))
    ).all()

    results = []
    for dec in decisions:
        event = session.get(PaymentEvent, dec.payment_event_id)
        if not event:
            continue

        cls = session.exec(
            select(Classification).where(Classification.id == dec.classification_id)
        ).first()

        audit = session.exec(
            select(AuditLog)
            .where(AuditLog.entity_type == "RecoveryDecision")
            .where(AuditLog.entity_id == dec.id)
        ).first()

        results.append(ExceptionRecord(
            event_id=event.id,
            order_id=event.order_id,
            customer_name=event.customer_name,
            amount=event.amount,
            bucket=cls.bucket if cls else "unknown",
            stopping_rule=dec.stopping_rule_triggered or "",
            rule_fired=dec.rule_fired,
            detail=audit.detail if audit else "",
        ))
    return results


@router.get("/{event_id}", response_model=RecordOut)
def get_record(event_id: int, session: Session = Depends(get_session)):
    event = session.get(PaymentEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    cls = session.exec(
        select(Classification).where(Classification.payment_event_id == event.id)
    ).first()
    dec = session.exec(
        select(RecoveryDecision).where(RecoveryDecision.payment_event_id == event.id)
    ).first()
    act = None
    if dec:
        act = session.exec(
            select(RecoveryAction).where(RecoveryAction.recovery_decision_id == dec.id)
        ).first()

    return _to_record(event, cls, dec, act)
