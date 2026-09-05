import asyncio
import logging

from sqlmodel import select

from core.config import get_settings
from core.services.razorpay_client import create_payment_link
from core.services.sarvam_client import draft_recovery_message
from models import PaymentEvent, Classification, RecoveryDecision, RecoveryAction, AuditLog

logger = logging.getLogger(__name__)


def _audit(session, entity_type: str, entity_id: int, actor: str, action: str, detail: str):
    session.add(AuditLog(
        entity_type=entity_type, entity_id=entity_id,
        actor=actor, action=action, detail=detail,
    ))
    session.commit()


def _bucket_for_decision(session, decision: RecoveryDecision) -> str:
    cls = session.get(Classification, decision.classification_id)
    return cls.bucket if cls else "insufficient_funds"


async def _payment_link_with_retries(event: PaymentEvent) -> dict:
    settings = get_settings()
    attempts = max(1, settings.action_retry_attempts + 1)
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            amount_paise = int(event.amount * 100)
            link_resp = await asyncio.to_thread(
                create_payment_link,
                amount_paise=amount_paise,
                currency=event.currency,
                description=f"Retry payment for order {event.order_id}",
                customer_name=event.customer_name,
                customer_email=event.customer_email,
                customer_phone=event.customer_phone,
                reference_id=event.order_id,
            )
            return link_resp
        except Exception as exc:
            last_error = exc
            logger.warning("payment link attempt %d/%d failed: %s",
                           attempt + 1, attempts, exc)
            if attempt < attempts - 1:
                await asyncio.sleep(1.0)

    raise last_error


async def _keyless_sandbox(session, decision, event, bucket) -> RecoveryAction | None:
    """Keyless demo path: records the action with a drafted message but no link."""
    draft = await draft_recovery_message(bucket, event.customer_name, event.amount)

    action_record = RecoveryAction(
        recovery_decision_id=decision.id,
        channel="sms",
        message_text=draft.message_en.replace("{retry_link}", "https://sandbox.example/link"),
        language="en",
        payment_link_url=None,
    )
    session.add(action_record)
    session.commit()
    session.refresh(action_record)
    _audit(session, "RecoveryAction", action_record.id, "system",
           "sandboxed", "no gateway key - sandbox action, no real link")
    return action_record


async def execute_recovery(
    session, event: PaymentEvent, decision: RecoveryDecision,
) -> RecoveryAction | None:
    action_type = decision.action

    if action_type == "no_action":
        _audit(session, "RecoveryDecision", decision.id, "system",
               "skip", f"No action: {decision.stopping_rule_triggered}")
        return None

    existing = session.exec(
        select(RecoveryAction)
        .where(RecoveryAction.recovery_decision_id == decision.id)
    ).first()
    if existing is not None:
        _audit(session, "RecoveryDecision", decision.id, "system",
               "skip", "action already exists for this decision, not re-running")
        return existing

    if action_type == "retry_link":
        bucket = _bucket_for_decision(session, decision)

        settings = get_settings()
        if not settings.razorpay_key_id:
            return await _keyless_sandbox(session, decision, event, bucket)

        try:
            link_resp = await _payment_link_with_retries(event)
            short_url = link_resp.get("short_url", "")
            _audit(session, "RecoveryDecision", decision.id, "system",
                   "link_created", f"payment link: {short_url}")

            draft = await draft_recovery_message(bucket, event.customer_name, event.amount)

            action_record = RecoveryAction(
                recovery_decision_id=decision.id,
                channel="sms",
                message_text=draft.message_en.replace("{retry_link}", short_url),
                language="en",
                payment_link_url=short_url,
            )
            session.add(action_record)
            session.commit()
            session.refresh(action_record)
            _audit(session, "RecoveryAction", action_record.id, "system",
                   "drafted", f"messages ready for link {short_url}")
            return action_record

        except Exception as exc:
            logger.error("retry_link failed: %s", exc)
            _audit(session, "RecoveryDecision", decision.id, "system", "failed", str(exc))
            return None

    if action_type in ("reminder", "escalate"):
        try:
            bucket = _bucket_for_decision(session, decision)
            draft = await draft_recovery_message(bucket, event.customer_name, event.amount)

            action_record = RecoveryAction(
                recovery_decision_id=decision.id,
                channel="email" if action_type == "reminder" else "whatsapp_sim",
                message_text=draft.message_en,
                language="en",
            )
            session.add(action_record)
            session.commit()
            session.refresh(action_record)
            _audit(session, "RecoveryAction", action_record.id, "system",
                   "drafted", f"{action_type} message drafted")
            return action_record

        except Exception as exc:
            logger.error("%s failed: %s", action_type, exc)
            _audit(session, "RecoveryDecision", decision.id, "system", "failed", str(exc))
            return None

    logger.warning("unknown action: %s", action_type)
    return None


def pending_decisions(session) -> list[RecoveryDecision]:
    """Decisions that want an action but have not produced one yet."""
    settings = get_settings()
    if settings.auto_execute:
        return []

    made = session.exec(
        select(RecoveryDecision)
        .where(RecoveryDecision.action != "no_action")
    ).all()

    pending = []
    for decision in made:
        existing = session.exec(
            select(RecoveryAction)
            .where(RecoveryAction.recovery_decision_id == decision.id)
        ).first()
        if existing is None:
            pending.append(decision)
    return pending