import logging

import razorpay
from razorpay.errors import BadRequestError, ServerError

from ..config import get_settings

logger = logging.getLogger(__name__)

_client: razorpay.Client | None = None


def _get_client():
    global _client
    if _client is None:
        s = get_settings()
        _client = razorpay.Client(auth=(s.razorpay_key_id, s.razorpay_key_secret))
    return _client


def create_order(amount_paise: int, currency: str = "INR", receipt: str = "") -> dict:
    client = _get_client()
    try:
        resp = client.order.create({
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
        })
        logger.info("order created: %s", resp.get("id"))
        return resp
    except (BadRequestError, ServerError) as exc:
        logger.error("order creation failed: %s", exc)
        raise


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


def fetch_payment(payment_id: str) -> dict:
    client = _get_client()
    try:
        return client.payment.fetch(payment_id)
    except (BadRequestError, ServerError) as exc:
        logger.error("payment fetch failed: %s", exc)
        raise
