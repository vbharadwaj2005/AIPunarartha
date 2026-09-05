from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select

from core.db import get_session
from core.schemas import RecordOut, ExceptionRecord, PendingActionOut, mask_email, mask_phone
from core.services.action_executor import execute_recovery, pending_decisions
from models import PaymentEvent, Classification, RecoveryDecision, RecoveryAction, AuditLog

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
        customer_phone=mask_phone(event.customer_phone),
        customer_email=mask_email(event.customer_email),
        customer_opted_out=event.customer_opted_out,
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
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    limit = min(limit, 2000)

    query = select(PaymentEvent)
    if status:
        query = query.where(PaymentEvent.status == status)
    if bucket:
        query = query.join(Classification, Classification.payment_event_id == PaymentEvent.id)
        query = query.where(Classification.bucket == bucket)
    if action:
        query = query.join(RecoveryDecision, RecoveryDecision.payment_event_id == PaymentEvent.id)
        query = query.where(RecoveryDecision.action == action)

    events = session.exec(query.distinct().offset(skip).limit(limit)).all()
    if not events:
        return []

    event_ids = [e.id for e in events]
    event_ids_in = tuple(event_ids)

    cls_map = {
        c.payment_event_id: c
        for c in session.exec(
            select(Classification).where(Classification.payment_event_id.in_(event_ids_in))
        ).all()
    }
    dec_map = {
        d.payment_event_id: d
        for d in session.exec(
            select(RecoveryDecision).where(RecoveryDecision.payment_event_id.in_(event_ids_in))
        ).all()
    }
    act_map = {}
    dec_ids = [d.id for d in dec_map.values()]
    if dec_ids:
        act_map = {
            a.recovery_decision_id: a
            for a in session.exec(
                select(RecoveryAction).where(RecoveryAction.recovery_decision_id.in_(tuple(dec_ids)))
            ).all()
        }

    results = []
    for event in events:
        dec = dec_map.get(event.id)
        act = act_map.get(dec.id) if dec else None
        results.append(_to_record(event, cls_map.get(event.id), dec, act))
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

        cls = session.get(Classification, dec.classification_id)

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


@router.get("/pending", response_model=list[PendingActionOut])
def list_pending(session: Session = Depends(get_session)):
    """Actions queued for a human when auto-execute is switched off."""
    results = []
    for decision in pending_decisions(session):
        event = session.get(PaymentEvent, decision.payment_event_id)
        cls = session.get(Classification, decision.classification_id)
        if not event or not cls:
            continue
        results.append(PendingActionOut(
            decision_id=decision.id,
            event_id=event.id,
            order_id=event.order_id,
            customer_name=event.customer_name,
            amount=event.amount,
            bucket=cls.bucket,
            action=decision.action,
            rule_fired=decision.rule_fired,
            created_at=decision.created_at,
        ))
    return results


@router.post("/pending/{decision_id}/execute")
async def approve_pending(
    decision_id: int,
    session: Session = Depends(get_session),
):
    """Human approves a queued recovery action; the decision is then executed.

    Idempotent: approving the same decision twice produces exactly one action.
    Approvals of decisions that a stopping rule had blocked are recorded as
    explicit human overrides in the audit trail.
    """
    decision = session.get(RecoveryDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="decision not found")

    if decision.action == "no_action":
        raise HTTPException(status_code=400, detail="decision has no action to execute")

    event = session.get(PaymentEvent, decision.payment_event_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")

    existing = session.exec(
        select(RecoveryAction).where(RecoveryAction.recovery_decision_id == decision.id)
    ).first()
    if existing is not None:
        return {"decision_id": decision.id, "executed": False, "already_executed": True}

    override = decision.stopping_rule_triggered is not None
    session.add(AuditLog(
        entity_type="RecoveryDecision", entity_id=decision.id,
        actor="human",
        action="approved_override" if override else "approved",
        detail=(
            f"human approved despite stopping rule: {decision.stopping_rule_triggered}"
            if override else "queued action approved by operator"
        ),
    ))
    session.commit()

    action = await execute_recovery(session, event, decision)
    return {
        "decision_id": decision.id,
        "executed": action is not None,
        "already_executed": False,
        "override": override,
    }


@router.get("/{event_id}", response_model=RecordOut)
def get_record(event_id: int, session: Session = Depends(get_session)):
    event = session.get(PaymentEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")

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