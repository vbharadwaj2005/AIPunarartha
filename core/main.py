import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.db import init_db
from core.routers import events, batch, records

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "aiartha.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(get_settings().log_level)
    root.addHandler(console)
    root.addHandler(file_handler)


_configure_logging()

app = FastAPI(
    title="AIArtha",
    description="AI revenue recovery - detect, classify and recover failed payments",
    version="0.2.0",
)

origin_list = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(batch.router)
app.include_router(records.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logging.getLogger("core").info("database ready")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aiartha", "version": "0.2.0"}