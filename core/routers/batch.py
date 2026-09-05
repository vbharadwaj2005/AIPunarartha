from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from core.config import get_settings
from core.db import get_session
from core.schemas import BatchSummary, DriftReport
from models import PaymentEvent, Classification, RecoveryDecision, RecoveryAction

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.get("/summary", response_model=BatchSummary)
def batch_summary(session: Session = Depends(get_session)):
    events = session.exec(select(PaymentEvent)).all()
    classifications = session.exec(select(Classification)).all()
    decisions = session.exec(select(RecoveryDecision)).all()
    actions = session.exec(select(RecoveryAction)).all()

    total_events = len(events)
    total_at_risk = sum(e.amount for e in events if e.status != "captured")

    total_recovered = 0.0
    decision_map = {d.id: d for d in decisions}
    event_map = {e.id: e for e in events}

    for act in actions:
        if act.outcome == "recovered":
            dec = decision_map.get(act.recovery_decision_id)
            if dec and dec.payment_event_id in event_map:
                total_recovered += event_map[dec.payment_event_id].amount

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


@router.get("/drift", response_model=DriftReport)
def batch_drift(session: Session = Depends(get_session)):
    """
    Compares the most recent events against everything that came before them,
    and flags buckets whose share of failures moved materially. Cheap, honest,
    and purely a heads-up for whoever owns the batch.
    """
    settings = get_settings()
    window = settings.drift_window_events
    threshold = settings.drift_threshold_pct

    ordered = session.exec(
        select(PaymentEvent).order_by(PaymentEvent.created_at)
    ).all()

    if len(ordered) <= window:
        return DriftReport(
            window_events=window, threshold_pct=threshold,
            sufficient_data=False, flag_raised=False,
            bucket_shifts={},
            recent_recovery_rate_pct=None,
            baseline_recovery_rate_pct=None,
        )

    baseline_events = ordered[:-window]
    recent_events = ordered[-window:]

    classifications = {c.payment_event_id: c for c in session.exec(select(Classification)).all()}

    def bucket_share(events) -> dict[str, float]:
        counts: dict[str, int] = {}
        total = 0
        for ev in events:
            cls = classifications.get(ev.id)
            if cls is None:
                continue
            counts[cls.bucket] = counts.get(cls.bucket, 0) + 1
            total += 1
        if total == 0:
            return {}
        return {bucket: round(count / total * 100, 1) for bucket, count in counts.items()}

    base_share = bucket_share(baseline_events)
    recent_share = bucket_share(recent_events)

    all_buckets = sorted(set(base_share) | set(recent_share))
    shifts = {
        bucket: round((recent_share.get(bucket, 0.0) - base_share.get(bucket, 0.0)), 1)
        for bucket in all_buckets
    }
    flag = any(abs(shift) >= threshold for shift in shifts.values())

    decision_map = {d.payment_event_id: d for d in session.exec(select(RecoveryDecision)).all()}
    action_map = {a.recovery_decision_id: a for a in session.exec(select(RecoveryAction)).all()}
    amount_map = {e.id: e.amount for e in ordered}

    def recovery_rate(events) -> float | None:
        recovered = at_risk = 0.0
        for ev in events:
            dec = decision_map.get(ev.id)
            if dec is None:
                continue
            act = action_map.get(dec.id)
            if act and act.outcome == "recovered":
                recovered += amount_map.get(ev.id, 0.0)
            if ev.status != "captured":
                at_risk += amount_map.get(ev.id, 0.0)
        if at_risk <= 0:
            return None
        return round(recovered / at_risk * 100, 1)

    return DriftReport(
        window_events=window,
        threshold_pct=threshold,
        sufficient_data=True,
        flag_raised=flag,
        bucket_shifts=shifts,
        recent_recovery_rate_pct=recovery_rate(recent_events),
        baseline_recovery_rate_pct=recovery_rate(baseline_events),
    )