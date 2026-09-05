import logging

import razorpay
from razorpay.errors import BadRequestError, ServerError

from core.config import get_settings

logger = logging.getLogger(__name__)

_client: razorpay.Client | None = None


def _get_client() -> razorpay.Client:
    global _client
    if _client is None:
        s = get_settings()
        if not s.razorpay_key_id or not s.razorpay_key_secret:
            raise RuntimeError(
                "Razorpay is not configured (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET "
                "missing from .env) - the app runs in keyless sandbox mode until keys are added."
            )
        _client = razorpay.Client(auth=(s.razorpay_key_id, s.razorpay_key_secret))
    return _client


def create_payment_link(
    amount_paise: int,
    currency: str = "INR",
    description: str = "",
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    reference_id: str = "",
) -> dict:
    client = _get_client()
    payload = {
        "amount": amount_paise,
        "currency": currency,
        "description": description or "Retry your payment",
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "contact": customer_phone,
        },
        "notify": {"sms": False, "email": False, "whatsapp": False},
        "reference_id": reference_id,
    }
    try:
        resp = client.payment_link.create(payload)
        logger.info("payment link created: %s", resp.get("short_url"))
        return resp
    except (BadRequestError, ServerError) as exc:
        logger.error("payment link failed: %s", exc)
        raise