import os
import logging
import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID_INVESTOR = os.getenv("TELEGRAM_CHAT_ID_INVESTOR", "")

_ready = False


def init():
    global _ready
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID_INVESTOR:
        _ready = True
        logger.info("Telegram client ready")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID_INVESTOR not set — Telegram disabled")


async def send_alert(title: str, message: str, severity: str = "info"):
    if not _ready:
        return
    try:
        icon = {"high": "\U0001F6A8", "medium": "\u26A0\uFE0F", "low": "\u2139\uFE0F"}.get(severity, "\u2139\uFE0F")
        text = f"{icon} *{title}*\n{message}"
        async with httpx.AsyncClient(timeout=10) as cl:
            await cl.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID_INVESTOR,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            )
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)
