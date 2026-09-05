#!/usr/bin/env python3
"""
Run the classification -> decision -> action pipeline over every event
in the database that has not been processed yet. Safe to re-run: already
classified events are skipped.

Usage:
    python -m core.scripts.run_pipeline
"""
import asyncio
from datetime import datetime, timezone

from sqlmodel import Session, select

from core.db import engine, init_db
from core.config import get_settings
from core.services.action_executor import execute_recovery
from core.services.classifier import resolve_bucket_by_rule
from core.services.decision_engine import evaluate_decision, build_order_history
from core.services.sarvam_client import classify_free_text
from models import PaymentEvent, Classification, RecoveryDecision, AuditLog


async def run_pipeline():
    init_db()

    with Session(engine) as session:
        events = session.exec(select(PaymentEvent)).all()
        print(f"Found {len(events)} events in the database.\n")

        classified = decisions = actions = 0

        for event in events:
            existing = session.exec(
                select(Classification).where(Classification.payment_event_id == event.id)
            ).first()

            if existing is None:
                code = event.failure_reason_code
                text = event.failure_reason_text
                bucket, reasoning = resolve_bucket_by_rule(code, text)

                if bucket is None:
                    llm = await classify_free_text(text or code or "unknown failure")
                    bucket = llm.bucket
                    confidence = llm.confidence
                    reasoning = f"[llm] {llm.reasoning}"
                    method = "llm"
                else:
                    method = "rule"
                    confidence = 1.0

                cls = Classification(
                    payment_event_id=event.id,
                    bucket=bucket, method=method,
                    confidence=confidence, reasoning_text=reasoning,
                )
                session.add(cls)
                session.commit()
                session.refresh(cls)
                classified += 1
                print(f"  [event {event.id}] {bucket} ({method})")
            else:
                cls = existing

            existing_dec = session.exec(
                select(RecoveryDecision).where(RecoveryDecision.payment_event_id == event.id)
            ).first()

            if existing_dec is not None:
                print(f"  [event {event.id}] already decided, skipping")
                continue

            prior = build_order_history(session, event)

            action, rule_fired, stopping = evaluate_decision(event, cls, list(prior))

            dec = RecoveryDecision(
                payment_event_id=event.id,
                classification_id=cls.id,
                action=action,
                stopping_rule_triggered=stopping,
                rule_fired=rule_fired,
                created_at=datetime.now(timezone.utc),
            )
            session.add(dec)
            session.commit()
            session.refresh(dec)
            decisions += 1

            if action != "no_action":
                if get_settings().auto_execute:
                    act = await execute_recovery(session, event, dec)
                    if act:
                        actions += 1
                        print(f"  [event {event.id}] -> {action} ({act.channel})")
                    else:
                        print(f"  [event {event.id}] -> {action} (provider skipped/failed)")
                else:
                    session.add(AuditLog(
                        entity_type="RecoveryDecision", entity_id=dec.id,
                        actor="system", action="pending_review",
                        detail="auto-execute is off; awaiting human approval",
                    ))
                    session.commit()
                    print(f"  [event {event.id}] -> {action} (queued for approval)")
            else:
                print(f"  [event {event.id}] -> no_action ({stopping})")

        print(f"\nDone: {classified} classified, {decisions} decided, {actions} executed.")


if __name__ == "__main__":
    asyncio.run(run_pipeline())