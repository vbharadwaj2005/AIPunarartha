#!/usr/bin/env python3
"""
Generate a synthetic batch of 55+ PaymentEvent rows for testing the pipeline.

Distribution targets:
  ~40% insufficient_funds, ~20% card_expired, ~15% bank_timeout,
  ~15% 3ds_failed, ~10% ambiguous (free-text, not in decline_rules.json)

Usage:
    cd backend
    python -m app.scripts.generate_synthetic_batch
"""
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import engine, init_db
from app.models import PaymentEvent
from sqlmodel import Session

fake = Faker("en_IN")

# Razorpay-style decline codes with realistic descriptions
DECLINE_CODES = {
    "insufficient_funds": [
        ("insufficient_funds", "Your account has insufficient balance"),
        ("insufficient_funds", "Not enough balance to complete this transaction"),
        ("EC_DECLINE_2059", "Insufficient funds for the transaction"),
    ],
    "card_expired": [
        ("expired_card", "Your card has expired"),
        ("invalid_card_expiry", "Card expiry date is invalid"),
        ("EC_DECLINE_2001", "Expired card"),
    ],
    "bank_timeout": [
        ("bank_timeout", "Bank server did not respond in time"),
        ("gateway_timeout", "Payment gateway timed out"),
        ("timed_out", "Transaction timed out — please try again"),
    ],
    "3ds_failed": [
        ("authentication_failed", "3D Secure authentication failed"),
        ("3d_authentication failed", "Cardholder could not complete authentication"),
        ("EC_DECLINE_2036", "Authentication failed at issuing bank"),
    ],
    "ambiguous": [
        (None, "kuch gadbad hai payment mein, samajh nahi aa raha"),
        (None, "transaction declined by bank without reason"),
        (None, "card se payment try kiya par nahi hua"),
        (None, "my payment is stuck, not sure what happened"),
        (None, "bank wale bol rahe hai card blocked hai but maine block nahi kiya"),
    ],
}

BUCKET_WEIGHTS = {
    "insufficient_funds": 40,
    "card_expired": 20,
    "bank_timeout": 15,
    "3ds_failed": 15,
    "ambiguous": 10,
}

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai",
    "Riya", "Ananya", "Diya", "Priya", "Kavya",
    "Rohan", "Meera", "Karan", "Nisha", "Tushar",
    "Sneha", "Amit", "Pooja", "Raj", "Neha",
    "Suresh", "Geeta", "Manoj", "Sunita", "Vikram",
    "Pallavi", "Deepak", "Rekha", "Sanjay", "Alka",
]

LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Reddy",
    "Nair", "Joshi", "Gupta", "Desai", "Rao",
    "Menon", "Iyer", "Chatterjee", "Mukherjee", "Bose",
]


def _random_amount():
    r = random.random()
    if r < 0.3:
        return round(random.uniform(99, 499), 2)
    elif r < 0.7:
        return round(random.uniform(500, 2999), 2)
    elif r < 0.9:
        return round(random.uniform(3000, 9999), 2)
    else:
        return round(random.uniform(10000, 49999), 2)


def _random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _random_phone():
    return f"+91{random.randint(6000000000, 9999999999)}"


def _random_email(name):
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com"])
    parts = name.lower().split()
    return f"{parts[0]}{parts[1]}{random.randint(1, 99)}@{domain}"


def generate_batch(size=55):
    events = []
    buckets = list(BUCKET_WEIGHTS.keys())
    weights = list(BUCKET_WEIGHTS.values())

    for i in range(size):
        bucket = random.choices(buckets, weights=weights, k=1)[0]
        code, reason_text = random.choice(DECLINE_CODES[bucket])
        name = _random_name()
        amount = _random_amount()

        # stagger created_at over the last 48 hours
        offset_hours = random.uniform(0, 48)
        created = datetime.now(timezone.utc) - timedelta(hours=offset_hours)

        events.append({
            "merchant_id": f"merch_{random.randint(1000, 9999)}",
            "order_id": f"order_{fake.uuid4()[:12]}",
            "amount": amount,
            "currency": "INR",
            "status": "failed",
            "failure_reason_code": code,
            "failure_reason_text": reason_text,
            "customer_name": name,
            "customer_phone": _random_phone(),
            "customer_email": _random_email(name),
            "created_at": created,
        })

    return events


def main():
    init_db()
    events = generate_batch(55)

    with Session(engine) as session:
        for data in events:
            session.add(PaymentEvent(**data))
        session.commit()

    print(f"Inserted {len(events)} synthetic PaymentEvent rows.")

    # quick breakdown
    counts = {}
    for e in events:
        code = (e["failure_reason_code"] or "").lower()
        text = (e["failure_reason_text"] or "").lower()
        if not e["failure_reason_code"]:
            b = "ambiguous"
        elif "insufficient" in code or "insufficient" in text:
            b = "insufficient_funds"
        elif "expired" in code or "expired" in text:
            b = "card_expired"
        elif "timeout" in code or "timeout" in text:
            b = "bank_timeout"
        elif "auth" in code or "3d" in code:
            b = "3ds_failed"
        else:
            b = "generic_decline"
        counts[b] = counts.get(b, 0) + 1

    print("Distribution:")
    for b, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {b}: {c} ({c / len(events) * 100:.0f}%)")


if __name__ == "__main__":
    main()
