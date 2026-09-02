#!/usr/bin/env python3
"""
Simulate recovery outcomes for all RecoveryActions in the DB.

These are NOT real outcomes — they're bucket-conditioned probabilities
based on industry data. We state this honestly in the README.

Usage:
    cd backend
    python -m app.scripts.simulate_outcomes
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import engine
from app.models import Classification, RecoveryDecision, RecoveryAction, AuditLog
from app.db import init_db
from sqlmodel import select, Session

# probability of recovery given an action was taken for each bucket
# (these are industry-informed guesses, not measured results)
RECOVERY_PROBS = {
    "insufficient_funds": 0.60,
    "bank_timeout": 0.70,
    "3ds_failed": 0.30,
    "card_expired": 0.05,
    "generic_decline": 0.15,
    "ambiguous": 0.10,
}


def main():
    init_db()
    with Session(engine) as session:
        actions = session.exec(select(RecoveryAction)).all()
        updated = 0
        skipped = 0

        for action in actions:
            if action.outcome is not None:
                skipped += 1
                continue

            decision = session.get(RecoveryDecision, action.recovery_decision_id)
            if not decision:
                continue

            cls = session.get(Classification, decision.classification_id)
            if not cls:
                continue

            prob = RECOVERY_PROBS.get(cls.bucket, 0.10)
            outcome = "recovered" if random.random() < prob else "still_failed"

            action.outcome = outcome
            session.add(action)
            session.add(AuditLog(
                entity_type="RecoveryAction", entity_id=action.id,
                actor="system", action="outcome_simulated",
                detail=f"Bucket: {cls.bucket}, prob={prob:.0%}, outcome={outcome}",
            ))
            updated += 1

        session.commit()
        print(f"Simulated outcomes for {updated} actions ({skipped} already had outcomes).")


if __name__ == "__main__":
    main()
