import html
import json
import time
import logging
import requests
from config import Config
import database

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Manages sending notifications and rich messages via Telegram Bot API."""

    def __init__(self, bot_token: str = None):
        self.bot_token = (bot_token or Config.TELEGRAM_BOT_TOKEN or "").strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        if self.is_configured():
            logger.info("[TelegramNotifier] Telegram Bot API initialized successfully.")
        else:
            logger.warning("[TelegramNotifier] TELEGRAM_BOT_TOKEN is not set. Running in dry-run/simulation mode.")

    def is_configured(self) -> bool:
        """Check if Telegram bot token is configured."""
        return bool(self.bot_token and self.base_url)

    def get_me(self) -> dict:
        """Verify bot credentials and get bot details."""
        if not self.is_configured():
            return {"ok": False, "error": "Bot token not configured"}
        try:
            resp = requests.get(f"{self.base_url}/getMe", timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"[TelegramNotifier] Error in getMe: {e}")
            return {"ok": False, "error": str(e)}

    def format_job_html(self, job: dict, matched_keywords: list[str]) -> str:
        """Format a single job alert into clean, rich Telegram HTML message."""
        source = job.get("source", "งานใหม่")
        group_raw = job.get("group_name") or "-"
        title_raw = job.get("title") or "ไม่มีหัวข้อ"
        budget_raw = job.get("budget")
        content_raw = (job.get("content") or "").strip()
        posted_label_raw = job.get("posted_label")

        # HTML Escape dynamic contents
        source_esc = html.escape(str(source))
        group_esc = html.escape(str(group_raw))
        title_esc = html.escape(str(title_raw))
        budget_esc = html.escape(str(budget_raw)) if budget_raw else ""
        posted_esc = html.escape(str(posted_label_raw)) if posted_label_raw else ""

        # Limit content preview
        summary = content_raw[:350] + "..." if len(content_raw) > 350 else (content_raw or "-")
        summary_esc = html.escape(summary)

        kws_str = ", ".join(matched_keywords) if matched_keywords else "-"
        kws_esc = html.escape(kws_str)

        header_icon = "💼" if "fastwork" in source.lower() else "📢"
        header = f"{header_icon} <b>[แจ้งเตือนงานใหม่: {source_esc}]</b>"
        if posted_esc:
            header += f" ({posted_esc})"

        lines = [header]

        if "facebook" in source.lower() and group_raw != "-":
            lines.append(f"👥 <b>กลุ่ม:</b> {group_esc}")

        lines.append(f"📌 <b>หัวข้อ:</b> {title_esc}")

        if budget_esc:
            lines.append(f"💰 <b>งบประมาณ:</b> <code>{budget_esc}</code>")

        lines.append(f"🎯 <b>ตรงกับ Prompt:</b> <code>{kws_esc}</code>\n")
        lines.append(f"📄 <b>รายละเอียดสรุป:</b>\n{summary_esc}")

        return "\n".join(lines)

    def create_inline_keyboard(self, url: str) -> dict:
        """Create an inline keyboard with a clickable button to open the job URL."""
        if not url or url == "-":
            return {}
        return {
            "inline_keyboard": [
                [
                    {"text": "👉 เปิดดูรายละเอียดประกาศงาน", "url": url}
                ]
            ]
        }

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: dict = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Send a text or HTML message to a specific Telegram chat_id.
        """
        if not self.is_configured():
            logger.info(f"[TelegramNotifier DRY-RUN] Would send to {chat_id}:\n{text}")
            return True

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=10)
            res_json = resp.json()
            if res_json.get("ok"):
                return True

            err_code = res_json.get("error_code")
            desc = res_json.get("description", "")
            logger.warning(f"[TelegramNotifier] Telegram API error for {chat_id}: [{err_code}] {desc}")

            # If bot was blocked by the user or chat not found, deactivate subscriber
            if err_code in (403, 400) and ("blocked" in desc.lower() or "chat not found" in desc.lower() or "deactivated" in desc.lower()):
                logger.info(f"[TelegramNotifier] Subscriber {chat_id} is unreachable. Deactivating...")
                database.remove_subscriber(str(chat_id))

            # If rate limited by Telegram (429)
            elif err_code == 429:
                retry_after = res_json.get("parameters", {}).get("retry_after", 3)
                logger.warning(f"[TelegramNotifier] Rate limited! Sleeping for {retry_after}s...")
                time.sleep(retry_after)

            return False
        except Exception as e:
            logger.error(f"[TelegramNotifier] Network exception sending to {chat_id}: {e}")
            return False

    def send_job_alert(self, job: dict, matched_keywords: list[str], target_ids: list[str] = None) -> int:
        """
        Send a job notification to subscribers via Telegram.
        Returns the number of successfully sent messages.
        """
        if not target_ids:
            target_ids = database.get_subscribers()

        if not target_ids:
            logger.warning("[TelegramNotifier] No subscribers registered to receive notifications.")
            return 0

        html_text = self.format_job_html(job, matched_keywords)
        keyboard = self.create_inline_keyboard(job.get("url", ""))

        if not self.is_configured():
            logger.info(f"[TelegramNotifier DRY-RUN] Would send to {len(target_ids)} subscribers:\n{html_text}")
            return len(target_ids)

        success_count = 0
        for target_id in target_ids:
            sent = self.send_message(
                chat_id=target_id,
                text=html_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            if sent:
                success_count += 1
            # Respect Telegram rate limit (up to 30 msgs/sec)
            time.sleep(0.04)

        logger.info(f"[TelegramNotifier] Alert sent to {success_count}/{len(target_ids)} targets.")
        return success_count
