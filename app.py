"""
app.py
Flask application — entry point for the WhatsApp bot.

Endpoints:
  GET  /webhook   — Meta webhook verification (one-time setup)
  POST /webhook   — Incoming WhatsApp messages
  GET  /ping      — Health check + keeps Render free tier awake
  GET  /refresh   — Force-reload config from Google Sheets (useful after editing Setup)
"""

import logging
import os
import requests

from flask import Flask, request, jsonify

import config
import conversation
import sheets

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ─── WhatsApp API ─────────────────────────────────────────────────────────────

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0/{phone_id}/messages"

def send_message(to: str, body: str) -> bool:
    """Send a WhatsApp text message to a phone number."""
    url = WHATSAPP_API_URL.format(phone_id=config.WHATSAPP_PHONE_ID)
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to":   to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Failed to send WhatsApp message to %s: %s", to, e)
        return False


# ─── Webhook endpoints ────────────────────────────────────────────────────────

@app.get("/webhook")
def verify_webhook():
    """
    Meta calls this once when you register the webhook URL.
    It sends hub.challenge — we echo it back to prove ownership.
    """
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge, 200

    logger.warning("Webhook verification failed (token mismatch or wrong mode)")
    return "Forbidden", 403


@app.post("/webhook")
def receive_message():
    """
    Meta POSTs every incoming WhatsApp message here.
    We extract the sender phone + text, run it through the state machine,
    and reply via the API.
    """
    data = request.get_json(silent=True) or {}

    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]["value"]

        # Ignore delivery/read receipts — they have no "messages" key
        messages = changes.get("messages")
        if not messages:
            return jsonify({"status": "ok"}), 200

        msg    = messages[0]
        phone  = msg["from"]                        # e.g. "351912345678"
        m_type = msg.get("type", "")

        # We only handle plain text messages
        if m_type != "text":
            send_message(phone, "👋 Please send text messages only.")
            return jsonify({"status": "ok"}), 200

        text = msg["text"]["body"]
        logger.info("Incoming from %s: %r", phone, text[:80])

        # Run through state machine
        reply = conversation.handle_message(phone, text)

        # Send reply
        sent = send_message(phone, reply)
        if not sent:
            logger.error("Reply not delivered to %s", phone)

    except (KeyError, IndexError, TypeError) as e:
        # Malformed payload — log and return 200 so Meta doesn't retry forever
        logger.warning("Unexpected webhook payload: %s  |  data=%s", e, str(data)[:200])

    return jsonify({"status": "ok"}), 200


# ─── Utility endpoints ────────────────────────────────────────────────────────

@app.get("/ping")
def ping():
    """
    Health check. Returns 200 so cron-job.org can keep the server warm.
    Also reported by uptime monitors.
    """
    return jsonify({"status": "alive", "bot": config.BOT_NAME}), 200


@app.get("/refresh")
def refresh_config():
    """
    Force-reload categories / accounts / members from the Setup sheet.
    Call this after editing the Setup sheet to pick up changes immediately
    (otherwise the cache refreshes automatically every hour).
    """
    sheets.force_refresh()
    cfg = sheets.get_config()
    summary = {k: len(v) for k, v in cfg.items()}
    logger.info("Config refreshed: %s", summary)
    return jsonify({"status": "refreshed", "counts": summary}), 200


# ─── Startup ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Pre-warm the Sheets config on startup so the first message is fast
    logger.info("Pre-loading config from Google Sheets...")
    sheets.get_config()
    logger.info("Bot '%s' ready.", config.BOT_NAME)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)