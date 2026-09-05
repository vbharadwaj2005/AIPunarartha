#!/usr/bin/env python3
"""
Simulate recovery outcomes for actions that do not have one yet.

Outcomes are NOT real results - they come from bucket-conditioned recovery
probabilities that are honest, industry-informed guesses. The README and the
dashboard both say so. Use --seed to reproduce a run exactly.

Usage:
    python -m core.scripts.simulate_outcomes [--seed 11]
"""
import argparse
import random
import sys

from sqlmodel import Session, select

from core.config import get_settings
from core.db import engine, init_db
from models import Classification, RecoveryDecision, RecoveryAction, AuditLog

RECOVERY_PROBS = {
    "insufficient_funds": 0.60,
    "bank_timeout": 0.70,
    "3ds_failed": 0.30,
    "card_expired": 0.05,
    "generic_decline": 0.15,
    "ambiguous": 0.10,
}


def main():
    parser = argparse.ArgumentParser(description="Simulate recovery outcomes.")
    parser.add_argument("--seed", type=int, default=get_settings().simulation_seed,
                        help="random seed for reproducibility")
    args = parser.parse_args()
    random.seed(args.seed)
    print(f"Seed: {args.seed}")

    init_db()
    with Session(engine) as session:
        actions = session.exec(select(RecoveryAction)).all()
        updated = skipped = 0

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
                detail=f"bucket: {cls.bucket}, prob={prob:.0%}, outcome={outcome}",
            ))
            updated += 1

        session.commit()
        print(f"Simulated outcomes for {updated} actions ({skipped} already had ones).")
        sys.exit(0)


if __name__ == "__main__":
    main()