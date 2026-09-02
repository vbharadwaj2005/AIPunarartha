import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models import PaymentEvent, RecoveryDecision, Classification

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_action_rules():
    with open(_DATA_DIR / "action_rules.json") as f:
        return json.load(f)


def evaluate_decision(
    event: PaymentEvent,
    classification: Classification,
    existing_decisions: list[RecoveryDecision],
) -> tuple[str, str, str | None]:
    """
    Pure deterministic decision engine. No LLM calls.
    Returns (action, rule_fired, stopping_rule_or_None).
    """
    config = _load_action_rules()
    bucket_cfg = config["buckets"].get(classification.bucket)
    stopping = config["stopping_rules"]

    if not bucket_cfg:
        logger.warning("no bucket config for '%s', escalating", classification.bucket)
        return "escalate", f"unknown_bucket_{classification.bucket}", None

    # stopping rules
    min_amount = stopping["min_amount_threshold_inr"]
    if event.amount < min_amount:
        reason = f"amount_below_threshold (₹{event.amount:.0f} < ₹{min_amount})"
        return "no_action", "stopping:amount_below_threshold", reason

    prior_retries = sum(
        1 for d in existing_decisions
        if d.action == "retry_link" and d.stopping_rule_triggered is None
    )
    max_retries = bucket_cfg["max_retries"]
    if prior_retries >= max_retries:
        reason = f"max_retries ({prior_retries}/{max_retries} for {classification.bucket})"
        return "no_action", f"stopping:max_retries_{classification.bucket}", reason

    cooldown_hours = stopping["cooldown_hours"]
    if existing_decisions:
        latest = existing_decisions[-1]
        elapsed = (datetime.now(timezone.utc) - latest.created_at).total_seconds() / 3600
        if elapsed < cooldown_hours:
            reason = f"cooldown ({elapsed:.1f}h < {cooldown_hours}h since last)"
            return "no_action", "stopping:cooldown_active", reason

    # pick action
    if classification.bucket in ("insufficient_funds", "bank_timeout", "3ds_failed"):
        action = bucket_cfg["preferred_action"] if prior_retries == 0 else bucket_cfg["fallback_action"]
    else:
        action = bucket_cfg["preferred_action"]

    rule = f"bucket:{classification.bucket}, retries:{prior_retries}, action:{action}"
    return action, rule, None
