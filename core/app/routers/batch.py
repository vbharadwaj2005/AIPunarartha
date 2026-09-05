from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import PaymentEvent, Classification, RecoveryDecision, RecoveryAction
from ..schemas import BatchSummary

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.get("/summary", response_model=BatchSummary)
def batch_summary(session: Session = Depends(get_session)):
    events = session.exec(select(PaymentEvent)).all()
    classifications = session.exec(select(Classification)).all()
    decisions = session.exec(select(RecoveryDecision)).all()
    actions = session.exec(select(RecoveryAction)).all()

    total_events = len(events)
    total_at_risk = sum(e.amount for e in events if e.status != "captured")

    # figure out how much money was recovered by matching
    # recovered actions back to their original events
    total_recovered = 0.0
    decision_map = {d.id: d for d in decisions}
    event_map = {e.id: e for e in events}

    for act in actions:
        if act.outcome == "recovered":
            dec = decision_map.get(act.recovery_decision_id)
            if dec:
                ev = event_map.get(dec.payment_event_id)
                if ev:
                    total_recovered += ev.amount

    exceptions = [d for d in decisions if d.stopping_rule_triggered is not None]
    rule_count = sum(1 for c in classifications if c.method == "rule")
    llm_count = sum(1 for c in classifications if c.method == "llm")

    by_bucket: dict[str, int] = {}
    for c in classifications:
        by_bucket[c.bucket] = by_bucket.get(c.bucket, 0) + 1

    by_action: dict[str, int] = {}
    for d in decisions:
        by_action[d.action] = by_action.get(d.action, 0) + 1

    recovery_pct = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0

    return BatchSummary(
        total_events=total_events,
        total_at_risk=total_at_risk,
        total_recovered=total_recovered,
        recovery_rate_pct=round(recovery_pct, 1),
        exception_count=len(exceptions),
        rule_vs_llm_ratio={"rule": rule_count, "llm": llm_count},
        by_bucket=by_bucket,
        by_action=by_action,
    )
