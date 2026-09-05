import logging

from ..models import PaymentEvent, RecoveryDecision, RecoveryAction, AuditLog
from .razorpay_client import create_payment_link
from .sarvam_client import draft_recovery_message

logger = logging.getLogger(__name__)


def _audit(session, entity_type: str, entity_id: int, actor: str, action: str, detail: str):
    session.add(AuditLog(
        entity_type=entity_type, entity_id=entity_id,
        actor=actor, action=action, detail=detail,
    ))
    session.commit()


async def execute_recovery(session, event: PaymentEvent, decision: RecoveryDecision) -> RecoveryAction | None:
    action_type = decision.action

    if action_type == "no_action":
        _audit(session, "RecoveryDecision", decision.id, "system", "skip", f"No action: {decision.stopping_rule_triggered}")
        return None

    if action_type == "retry_link":
        try:
            amount_paise = int(event.amount * 100)
            link_resp = create_payment_link(
                amount_paise=amount_paise,
                currency=event.currency,
                description=f"Retry payment for order {event.order_id}",
                customer_name=event.customer_name,
                customer_email=event.customer_email,
                customer_phone=event.customer_phone,
                reference_id=event.order_id,
            )
            short_url = link_resp.get("short_url", "")
            _audit(session, "RecoveryDecision", decision.id, "system", "link_created", f"Payment link: {short_url}")

            draft = await draft_recovery_message("retry", event.customer_name, event.amount)
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
            _audit(session, "RecoveryAction", action_record.id, "system", "drafted", f"Messages for link {short_url}")
            return action_record

        except Exception as exc:
            logger.error("retry_link failed: %s", exc)
            _audit(session, "RecoveryDecision", decision.id, "system", "failed", str(exc))
            return None

    if action_type in ("reminder", "escalate"):
        try:
            draft = await draft_recovery_message(action_type, event.customer_name, event.amount)
            action_record = RecoveryAction(
                recovery_decision_id=decision.id,
                channel="email" if action_type == "reminder" else "whatsapp_sim",
                message_text=draft.message_en,
                language="hi-en",
            )
            session.add(action_record)
            session.commit()
            session.refresh(action_record)
            _audit(session, "RecoveryAction", action_record.id, "system", "drafted", f"{action_type} message drafted")
            return action_record

        except Exception as exc:
            logger.error("%s failed: %s", action_type, exc)
            _audit(session, "RecoveryDecision", decision.id, "system", "failed", str(exc))
            return None

    logger.warning("unknown action: %s", action_type)
    return None
