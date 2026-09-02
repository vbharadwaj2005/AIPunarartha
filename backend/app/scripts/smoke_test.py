#!/usr/bin/env python3
"""
Quick connectivity check for Razorpay and Sarvam APIs.
Doesn't modify anything — just prints whether keys work.

Usage:
    cd backend
    python -m app.scripts.smoke_test
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings


def test_razorpay():
    print("--- Razorpay ---")
    s = get_settings()
    key_ok = s.razorpay_key_id.startswith("rzp_test_") and len(s.razorpay_key_secret) > 10
    print(f"  Credentials: {'configured' if key_ok else 'NOT SET — update .env'}")

    if not key_ok:
        return False

    try:
        from app.services.razorpay_client import create_order
        resp = create_order(amount_paise=100, receipt="smoke_test")
        print(f"  Test order: {resp.get('id')} ({resp.get('status')})")
        return True
    except Exception as exc:
        print(f"  Failed: {exc}")
        return False


async def test_sarvam():
    print("\n--- Sarvam AI ---")
    s = get_settings()
    key_ok = len(s.sarvam_api_key) > 10
    print(f"  API key: {'configured' if key_ok else 'NOT SET — update .env'}")

    if not key_ok:
        return False

    try:
        from app.services.sarvam_client import classify_free_text
        result = await classify_free_text("mera card expire ho gaya hai, payment nahi ho rahi")
        print(f"  Result: bucket={result.bucket}, conf={result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        return True
    except Exception as exc:
        print(f"  Failed: {exc}")
        return False


async def main():
    r = test_razorpay()
    s = await test_sarvam()
    print(f"\nRazorpay={'OK' if r else 'SKIPPED'}, Sarvam={'OK' if s else 'SKIPPED'}")


if __name__ == "__main__":
    asyncio.run(main())
