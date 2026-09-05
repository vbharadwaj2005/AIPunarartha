import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import select

from models import PaymentEvent, RecoveryDecision, Classification

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_action_rules: dict = {}


def _load_action_rules():
    global _action_rules
    if not _action_rules:
        with open(_DATA_DIR / "action_rules.json") as f:
            _action_rules = json.load(f)
    return _action_rules


@dataclass
class PriorAttempt:
    """One earlier recovery decision for the same order (across all its failures)."""

    action: str
    bucket: str
    created_at: datetime
    stopped: bool


def build_order_history(session, event: PaymentEvent) -> list[PriorAttempt]:
    """Pull every recovery decision made for the same merchant+order, oldest first.

    This is what makes the retry budget and the cooldown real: they are enforced
    across repeated failures of one order, not just inside a single event row.
    """
    prior_events = session.exec(
        select(PaymentEvent).where(
            PaymentEvent.merchant_id == event.merchant_id,
            PaymentEvent.order_id == event.order_id,
        )
    ).all()
    event_ids = [e.id for e in prior_events]
    if not event_ids:
        return []

    decisions = session.exec(
        select(RecoveryDecision)
        .where(RecoveryDecision.payment_event_id.in_(event_ids))
        .order_by(RecoveryDecision.created_at)
    ).all()
    if not decisions:
        return []

    class_ids = {d.classification_id for d in decisions}
    buckets = {
        c.id: c.bucket
        for c in session.exec(select(Classification).where(Classification.id.in_(class_ids))).all()
    }

    return [
        PriorAttempt(
            action=d.action,
            bucket=buckets.get(d.classification_id, "unknown"),
            created_at=d.created_at,
            stopped=d.stopping_rule_triggered is not None,
        )
        for d in decisions
    ]


def evaluate_decision(
    event: PaymentEvent,
    classification: Classification,
    prior: list[PriorAttempt],
) -> tuple[str, str, str | None]:
    """
    Deterministic decision logic driven entirely by action_rules.json.
    Returns (action, rule_fired, stopping_rule_or_none).

    Retry budgets ('max_retries' per bucket and 'max_retries_global') apply to
    retry-link attempts only; reminders and escalations are not retries. The
    cooldown is a dunning pause: the engine keeps quiet while this order was
    already contacted recently, and honours the per-bucket retry delay before
    repeating the same bucket.
    """
    config = _load_action_rules()
    bucket_cfg = config["buckets"].get(classification.bucket)
    stopping = config["stopping_rules"]

    if event.customer_opted_out:
        return "no_action", "stopping:opted_out", "customer opted out of recovery"

    if not bucket_cfg:
        logger.warning("no bucket config for '%s', escalating", classification.bucket)
        return "escalate", f"unknown_bucket_{classification.bucket}", None

    min_amount = stopping["min_amount_threshold_inr"]
    if event.amount < min_amount:
        reason = f"amount_below_threshold (Rs.{event.amount:.0f} < Rs.{min_amount})"
        return "no_action", "stopping:amount_below_threshold", reason

    same_bucket_retries = sum(
        1 for p in prior if p.action == "retry_link" and p.bucket == classification.bucket
    )
    bucket_cap = bucket_cfg["max_retries"]

    attempts = [p for p in prior if p.action != "no_action"]
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    if attempts:
        latest = attempts[-1]
        elapsed_h = (now_naive - latest.created_at).total_seconds() / 3600
        if elapsed_h < stopping["cooldown_hours"]:
            reason = f"cooldown ({elapsed_h:.1f}h < {stopping['cooldown_hours']}h since last attempt)"
            return "no_action", "stopping:cooldown_active", reason

        same_bucket_latest = None
        for p in reversed(attempts):
            if p.bucket == classification.bucket:
                same_bucket_latest = p
                break
        if same_bucket_latest is not None:
            retry_delay = bucket_cfg.get("retry_delay_hours", 0)
            if retry_delay > 0:
                delay_elapsed = (now_naive - same_bucket_latest.created_at).total_seconds() / 3600
                if delay_elapsed < retry_delay:
                    reason = (f"retry_delay ({delay_elapsed:.1f}h < {retry_delay}h "
                              f"before repeating {classification.bucket})")
                    return "no_action", "stopping:retry_delay_active", reason

    if classification.bucket in ("insufficient_funds", "bank_timeout", "3ds_failed"):
        if same_bucket_retries < bucket_cap:
            action = bucket_cfg["preferred_action"]
        else:
            action = bucket_cfg["fallback_action"]
    else:
        action = bucket_cfg["preferred_action"]

    if action == "retry_link":
        total_retries = sum(1 for p in prior if p.action == "retry_link")
        global_cap = stopping["max_retries_global"]
        if total_retries >= global_cap:
            reason = f"max_retries_global ({total_retries}/{global_cap}) across all buckets"
            return "no_action", "stopping:max_retries_global", reason

        if same_bucket_retries >= bucket_cap:
            reason = f"max_retries ({same_bucket_retries}/{bucket_cap} for {classification.bucket})"
            return "no_action", f"stopping:max_retries_{classification.bucket}", reason

    rule = f"bucket:{classification.bucket}, retries:{same_bucket_retries}, action:{action}"
    return action, rule, None