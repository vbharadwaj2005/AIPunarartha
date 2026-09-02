import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_code_to_bucket: dict[str, str] | None = None


def _load_rules():
    global _code_to_bucket
    if _code_to_bucket is not None:
        return _code_to_bucket

    with open(_DATA_DIR / "decline_rules.json") as f:
        rules = json.load(f)["rules"]

    _code_to_bucket = {}
    for bucket, info in rules.items():
        for code in info["codes"]:
            _code_to_bucket[code.strip().lower()] = bucket
    return _code_to_bucket


def resolve_bucket_by_rule(code: str | None, text: str | None) -> tuple[str | None, str]:
    mapping = _load_rules()

    if code:
        found = mapping.get(code.strip().lower())
        if found:
            return found, f"Rule match: '{code}' -> '{found}'"

    if text:
        found = mapping.get(text.strip().lower())
        if found:
            return found, f"Rule match: '{text}' -> '{found}'"

    return None, "No rule matched — needs LLM"
