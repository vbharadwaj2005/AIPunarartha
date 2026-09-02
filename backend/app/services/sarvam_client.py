import json
import logging

import httpx
from pydantic import BaseModel

from ..config import get_settings

logger = logging.getLogger(__name__)

SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"

CLASSIFY_SYSTEM_PROMPT = """\
You are a payment failure classifier for an Indian fintech recovery system.
Given a raw failure reason (may be English, Hindi, or Hinglish, may be vague), \
classify it into exactly one of these buckets:
insufficient_funds, card_expired, bank_timeout, 3ds_failed, generic_decline, ambiguous.
Respond with ONLY valid JSON:
{"bucket": "<one of the above>", "confidence": <float 0-1>, "reasoning": "<one sentence>"}
If not confident, use "ambiguous" rather than guessing.
"""

MESSAGE_SYSTEM_PROMPT = """\
You are drafting a short, warm, non-pushy payment recovery message for an Indian customer whose payment failed.
Given the failure bucket, customer name, and amount, write:
1. A concise English version (max 2 sentences, include {retry_link} placeholder)
2. A natural Hinglish (code-mixed Hindi-English, Latin script) version
Respond with ONLY valid JSON: {"message_en": "...", "message_hi_en": "..."}
Do not sound like a debt collector. Be brief and friendly.
"""


class ClassificationResult(BaseModel):
    bucket: str
    confidence: float
    reasoning: str


class MessageDraft(BaseModel):
    message_en: str
    message_hi_en: str


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return text


async def _chat(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "model": SARVAM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(SARVAM_CHAT_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


async def classify_free_text(failure_text: str) -> ClassificationResult:
    """Route ambiguous/free-text failure reasons through Sarvam."""
    try:
        raw = await _chat(CLASSIFY_SYSTEM_PROMPT, failure_text)
        parsed = json.loads(_strip_fences(raw))
        result = ClassificationResult(**parsed)
        valid_buckets = {"insufficient_funds", "card_expired", "bank_timeout", "3ds_failed", "generic_decline", "ambiguous"}
        if result.bucket not in valid_buckets:
            logger.warning("Sarvam returned bad bucket: %s", result.bucket)
            return ClassificationResult(bucket="ambiguous", confidence=0.0, reasoning=f"Unknown bucket from LLM: {result.bucket}")
        return result
    except Exception as exc:
        logger.error("Sarvam classify failed: %s", exc)
        return ClassificationResult(bucket="ambiguous", confidence=0.0, reasoning=f"Sarvam error: {exc}")


async def draft_recovery_message(bucket: str, customer_name: str, amount: float) -> MessageDraft:
    prompt = f"Bucket: {bucket}\nCustomer: {customer_name}\nAmount: ₹{amount:.0f}"
    fallback_en = f"Hi {customer_name}, your payment of ₹{amount:.0f} couldn't be completed. Please try again: {{retry_link}}"
    fallback_hi = f"Hi {customer_name}, aapka ₹{amount:.0f} payment nahi ho paya. Dobara try karein: {{retry_link}}"
    try:
        raw = await _chat(MESSAGE_SYSTEM_PROMPT, prompt)
        parsed = json.loads(_strip_fences(raw))
        return MessageDraft(**parsed)
    except Exception as exc:
        logger.error("Sarvam draft failed: %s", exc)
        return MessageDraft(message_en=fallback_en, message_hi_en=fallback_hi)
