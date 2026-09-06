import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_webhook_secret: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./aipunarartha.db")

    auto_execute: bool = os.getenv("AUTO_EXECUTE", "true").lower() == "true"
    action_retry_attempts: int = int(os.getenv("ACTION_RETRY_ATTEMPTS", "2"))
    max_events_per_ip_per_minute: int = int(os.getenv("MAX_EVENTS_PER_IP_PER_MINUTE", "120"))

    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    llm_cache_capacity: int = int(os.getenv("LLM_CACHE_CAPACITY", "200"))
    llm_breaker_failures: int = int(os.getenv("LLM_BREAKER_FAILURES", "3"))
    llm_breaker_cooldown_seconds: int = int(os.getenv("LLM_BREAKER_COOLDOWN_SECONDS", "60"))

    simulation_seed: int = int(os.getenv("SIMULATION_SEED", "11"))

    drift_window_events: int = int(os.getenv("DRIFT_WINDOW_EVENTS", "30"))
    drift_threshold_pct: float = float(os.getenv("DRIFT_THRESHOLD_PCT", "15.0"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501,http://localhost:8000,http://127.0.0.1:8000",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()