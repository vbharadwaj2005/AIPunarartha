#!/usr/bin/env python3
"""
Generate a synthetic batch of PaymentEvent rows so the pipeline and
dashboard can be exercised locally without real gateway traffic.

Usage:
    python -m core.scripts.generate_synthetic_batch
"""
import random
from datetime import datetime, timezone, timedelta

from faker import Faker
from sqlmodel import Session

from core.db import engine, init_db
from models import PaymentEvent

fake = Faker("en_IN")

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
        ("timed_out", "Transaction timed out - please try again"),
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


def batch_events(size=55):
    events = []
    buckets = list(BUCKET_WEIGHTS.keys())
    weights = list(BUCKET_WEIGHTS.values())

    for _ in range(size):
        bucket = random.choices(buckets, weights=weights, k=1)[0]
        code, reason = random.choice(DECLINE_CODES[bucket])
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        amount = _random_amount()
        offset = random.uniform(0, 48)
        created = datetime.now(timezone.utc) - timedelta(hours=offset)

        events.append({
            "merchant_id": f"merch_{random.randint(1000, 9999)}",
            "order_id": f"order_{fake.uuid4()[:12]}",
            "amount": amount,
            "currency": "INR",
            "status": "failed",
            "failure_reason_code": code,
            "failure_reason_text": reason,
            "customer_name": name,
            "customer_phone": f"+91{random.randint(6000000000, 9999999999)}",
            "customer_email": _random_email(name),
            "customer_opted_out": random.random() < 0.03,
            "created_at": created,
        })
    return events


def _random_amount():
    r = random.random()
    if r < 0.3:
        return round(random.uniform(99, 499), 2)
    if r < 0.7:
        return round(random.uniform(500, 2999), 2)
    if r < 0.9:
        return round(random.uniform(3000, 9999), 2)
    return round(random.uniform(10000, 49999), 2)


def _random_email(name):
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com"])
    parts = name.lower().split()
    return f"{parts[0]}{parts[1]}{random.randint(1, 99)}@{domain}"


def main():
    init_db()
    events = batch_events(55)

    with Session(engine) as session:
        for data in events:
            session.add(PaymentEvent(**data))
        session.commit()

    print(f"Inserted {len(events)} synthetic events.")

    counts = {}
    for e in events:
        code = (e["failure_reason_code"] or "").lower()
        text = (e["failure_reason_text"] or "").lower()
        if not e["failure_reason_code"]:
            bucket = "ambiguous"
        elif "insufficient" in code or "insufficient" in text:
            bucket = "insufficient_funds"
        elif "expired" in code or "expired" in text:
            bucket = "card_expired"
        elif "timeout" in code or "timeout" in text:
            bucket = "bank_timeout"
        elif "auth" in code or "3d" in code:
            bucket = "3ds_failed"
        else:
            bucket = "generic_decline"
        counts[bucket] = counts.get(bucket, 0) + 1

    print("Distribution:")
    for bucket, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {bucket}: {count} ({count / len(events) * 100:.0f}%)")


if __name__ == "__main__":
    main()