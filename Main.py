import os
import sys
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Set stdout/stderr encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import Config
import database
from notifier.telegram_notifier import TelegramNotifier
from telegram_handler import TelegramCommandHandler
from telegram_polling import TelegramPollingWorker
from worker import JobMonitorWorker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TelegramBotFwFB")

app = Flask(__name__)

# Initialize components
database.init_db()
notifier = TelegramNotifier()
command_handler = TelegramCommandHandler(notifier)
polling_worker = TelegramPollingWorker(notifier, command_handler)
job_worker = JobMonitorWorker(notifier)

# Start background monitoring worker
job_worker.start()

# Start Telegram Polling if mode is polling
if Config.TELEGRAM_MODE == "polling":
    polling_worker.start()
else:
    logger.info(f"[Main] Running in Webhook mode. Set webhook to /telegram/webhook endpoint.")

# Start Keep-Alive pinger for cloud platforms (e.g. Render Free Tier)
def _start_keep_alive():
    import time
    import threading
    import requests
    target_url = os.getenv("RENDER_EXTERNAL_URL", "").strip() or os.getenv("KEEP_ALIVE_URL", "").strip()
    if not target_url:
        return

    health_url = f"{target_url.rstrip('/')}/health"
    def _ping_loop():
        logger.info(f"[KeepAlive] Started keep-alive pinger for: {health_url}")
        time.sleep(60)
        while True:
            try:
                requests.get(health_url, timeout=10)
                logger.info("[KeepAlive] Self-ping sent to keep service awake.")
            except Exception as e:
                logger.debug(f"[KeepAlive] Ping failed: {e}")
            time.sleep(600)  # Ping every 10 minutes

    threading.Thread(target=_ping_loop, daemon=True, name="KeepAliveWorker").start()

_start_keep_alive()


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Railway and status monitoring."""
    stats = database.get_stats()
    bot_info = notifier.get_me() if notifier.is_configured() else {"ok": False, "note": "Token not set"}
    return jsonify({
        "status": "online",
        "service": "Telegram Job Alert Bot (Fastwork & Facebook)",
        "version": "1.0.0",
        "mode": Config.TELEGRAM_MODE,
        "polling_running": polling_worker.is_running,
        "job_worker_running": job_worker.is_running,
        "poll_interval_seconds": Config.POLL_INTERVAL_SECONDS,
        "facebook_groups_count": len(Config.FB_GROUP_IDS),
        "telegram_configured": notifier.is_configured(),
        "telegram_bot_info": bot_info,
        "stats": stats
    }), 200


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """
    Telegram Webhook endpoint (used when TELEGRAM_MODE=webhook).
    """
    # Optional secret validation
    if Config.TELEGRAM_WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret_header != Config.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("[Webhook] Unauthorized secret token received.")
            return "Unauthorized", 401

    update = request.get_json(force=True, silent=True)
    if not update:
        return "No JSON payload", 400

    # 1. Standard text message
    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type", "user")
        from_user = msg.get("from", {})
        first_name = from_user.get("first_name", "")
        last_name = from_user.get("last_name", "")
        user_name = f"{first_name} {last_name}".strip() or from_user.get("username", "")
        text = msg.get("text", "")

        if chat_id and text:
            try:
                command_handler.handle_message(
                    chat_id=chat_id,
                    text=text,
                    user_name=user_name,
                    chat_type=chat_type
                )
            except Exception as e:
                logger.error(f"[Webhook] Error processing message: {e}")

    # 2. Callback query from button click
    elif "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")
        from_user = cb.get("from", {})
        user_name = from_user.get("first_name", "")
        data_text = cb.get("data", "")

        polling_worker._answer_callback_query(cb_id)

        if chat_id and data_text:
            try:
                command_handler.handle_message(
                    chat_id=chat_id,
                    text=data_text,
                    user_name=user_name
                )
            except Exception as e:
                logger.error(f"[Webhook] Error processing callback query: {e}")

    return "OK", 200


@app.route("/api/trigger-scrape", methods=["POST"])
def trigger_scrape():
    """Manual trigger endpoint for immediate scraping cycle."""
    logger.info("[API] Manual scrape cycle triggered.")
    stats = job_worker.check_jobs()
    return jsonify({
        "status": "success",
        "message": "Scrape cycle completed",
        "stats": stats
    }), 200


@app.route("/api/send-test", methods=["POST"])
def send_test_notification():
    """Trigger a sample test notification to all active Telegram subscribers."""
    sample_job = {
        "source": "Fastwork",
        "group_name": "Web & Programming",
        "title": "Full-Stack Web Developer (React + Python FastAPI)",
        "budget": "35,000 บาท",
        "content": "ต้องการฟรีแลนซ์พัฒนาระบบหลังบ้านและหน้าบ้านสำหรับระบบจัดการสินค้าและแดชบอร์ด AI มี API พร้อมเชื่อมต่อ สามารถเริ่มงานได้ทันที",
        "url": "https://fastwork.co",
        "posted_label": "🟢 ทดสอบระบบ"
    }

    matched_keywords = ["web", "react", "python", "ai", "ทดสอบ"]
    target_ids = database.get_subscribers()

    if not target_ids:
        return jsonify({"status": "no_subscribers", "message": "No subscribers registered."}), 200

    sent_count = notifier.send_job_alert(sample_job, matched_keywords, target_ids=target_ids)
    return jsonify({
        "status": "success",
        "sent_count": sent_count,
        "total_subscribers": len(target_ids)
    }), 200


@app.route("/api/simulate-job", methods=["POST"])
def simulate_job_webhook():
    """Simulate receiving a job from Facebook or Fastwork via JSON webhook."""
    data = request.get_json(silent=True) or {}
    post_item = {
        "source": data.get("source", "Facebook"),
        "group_name": data.get("group_name", "สมาคมโปรแกรมเมอร์ไทย"),
        "title": data.get("title", "รับฟรีแลนซ์พัฒนาเว็บด่วน"),
        "content": data.get("content", "ต้องการคนทำเว็บ React + Node.js งบ 25000 บาท"),
        "budget": data.get("budget", "25,000 บาท"),
        "url": data.get("url", "https://facebook.com/groups/thaiprogrammer"),
        "post_id": data.get("post_id", f"sim_{int(datetime.utcnow().timestamp())}")
    }

    subscribers = database.get_subscribers()
    user_prompts = database.get_all_user_prompts()
    default_prompt = Config.DEFAULT_PROMPT

    matched_subs, matched_terms = job_worker._evaluate_job_for_subscribers(
        post_item, subscribers, user_prompts, default_prompt
    )

    if matched_subs:
        full_id = f"{post_item['source'].lower()}_{post_item['post_id']}"
        pending_subs = database.get_subscribers_pending_for_job(matched_subs, full_id)

        if pending_subs:
            notifier.send_job_alert(post_item, matched_terms, target_ids=pending_subs)
            for sub_id in pending_subs:
                database.record_subscriber_received_job(sub_id, full_id)

            database.log_job(
                post_id=full_id,
                source=post_item["source"],
                group_name=post_item["group_name"],
                title=post_item["title"],
                content=post_item["content"],
                budget=post_item["budget"],
                url=post_item["url"],
                matched_keywords=", ".join(matched_terms)
            )
            return jsonify({
                "status": "matched_and_alerted",
                "matched_terms": matched_terms,
                "alerted_subscribers_count": len(pending_subs)
            }), 200
        else:
            return jsonify({"status": "skipped", "reason": "already_received_by_all_matched_subscribers"}), 200

    return jsonify({"status": "skipped", "reason": "no_prompt_match"}), 200


if __name__ == "__main__":
    port = Config.PORT
    logger.info(f"Starting Telegram Job Alert Bot on port {port} (Mode: {Config.TELEGRAM_MODE})...")
    app.run(host="0.0.0.0", port=port)
