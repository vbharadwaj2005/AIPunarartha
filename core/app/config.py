import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

# load .env from backend/ root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_webhook_secret: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./aipunarartha.db")
    ngrok_auth_token: str = os.getenv("NGROK_AUTH_TOKEN", "")
    fastapi_base_url: str = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


@lru_cache
def get_settings() -> Settings:
    return Settings()
