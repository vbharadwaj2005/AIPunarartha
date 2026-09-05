#!/usr/bin/env python3
"""
Run the full classification -> decision -> action pipeline on all
unprocessed PaymentEvent rows in the database.

Usage:
    cd backend
    python -m app.scripts.run_pipeline
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import engine, init_db, Session
from app.models import PaymentEvent, Classification, RecoveryDecision
from app.services.classifier import resolve_bucket_by_rule
from app.services.sarvam_client import classify_free_text
from app.services.decision_engine import evaluate_decision
from app.services.action_executor import execute_recovery
from sqlmodel import select


async def run_pipeline():
    init_db()

    with Session(engine) as session:
        events = session.exec(select(PaymentEvent)).all()
        print(f"Found {len(events)} events in DB.\n")

        classified = 0
        decisions = 0
        actions = 0

        for event in events:
            # check if already classified
            existing_cls = session.exec(
                select(Classification).where(Classification.payment_event_id == event.id)
            ).first()

            if existing_cls is None:
                code = event.failure_reason_code
                text = event.failure_reason_text
                bucket, reasoning = resolve_bucket_by_rule(code, text)

                if bucket is None:
                    # fall back to LLM
                    llm = await classify_free_text(text or code or "unknown failure")
                    bucket = llm.bucket
                    confidence = llm.confidence
                    reasoning = f"[LLM] {llm.reasoning}"
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
                print(f"  [{event.id}] {bucket} ({method})")
            else:
                cls = existing_cls

            # check if already has a decision
            existing_dec = session.exec(
                select(RecoveryDecision).where(RecoveryDecision.payment_event_id == event.id)
            ).first()

            if existing_dec is None:
                prior = session.exec(
                    select(RecoveryDecision)
                    .where(RecoveryDecision.payment_event_id == event.id)
                    .order_by(RecoveryDecision.created_at)
                ).all()

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
                    act = await execute_recovery(session, event, dec)
                    if act:
                        actions += 1
                        print(f"  [{event.id}] -> {action} ({act.channel})")
                    else:
                        print(f"  [{event.id}] -> {action} (failed)")
                else:
                    print(f"  [{event.id}] -> no_action ({stopping})")
            else:
                print(f"  [{event.id}] already done, skipping")

        print(f"\nDone: {classified} classified, {decisions} decisions, {actions} actions")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
