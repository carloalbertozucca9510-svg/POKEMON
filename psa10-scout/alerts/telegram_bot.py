"""
Telegram alerter — sends deal notifications to your Telegram chat.

Setup:
  1. Message @BotFather on Telegram → /newbot → copy token to .env
  2. Send any message to your new bot
  3. Run scripts/get_chat_id.py to get your chat ID → paste into .env
"""
import requests
from loguru import logger
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_deal_alert(deal: dict):
    """Send a formatted deal alert to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping alert")
        return

    discount_pct = round(deal["discount_pct"] * 100, 1)
    fire_tag = "🔥 FIRE DEAL" if deal["is_fire_deal"] else "✅ Good deal"

    text = (
        f"{fire_tag}\n\n"
        f"🃏 *{deal['card_name']}* — PSA 10\n"
        f"💰 Ask: *${deal['ask_price']:,.0f}*\n"
        f"📊 FMV (90d avg): ${deal['fmv_90d']:,.0f}\n"
        f"🏷 Discount: *-{discount_pct}%*\n"
        f"⭐ Score: {deal['deal_score']}/100\n\n"
        f"🔗 [View listing]({deal['listing_url']})"
    )

    _send(text)


def send_daily_summary(deals: list[dict]):
    """Send a daily digest of top deals."""
    if not deals:
        return
    lines = [f"📋 *Daily Summary — {len(deals)} deals found*\n"]
    top = sorted(deals, key=lambda x: x["deal_score"], reverse=True)[:10]
    for d in top:
        disc = round(d["discount_pct"] * 100, 1)
        lines.append(f"• {d['card_name']} — -{disc}% (score: {d['deal_score']})")
    _send("\n".join(lines))


def _send(text: str):
    """Raw Telegram message sender."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     text,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram alert sent")
    except Exception as e:
        logger.error("Telegram send failed: {}", e)
