import time
import logging
import threading
import requests
from config import Config
from notifier.telegram_notifier import TelegramNotifier
from telegram_handler import TelegramCommandHandler

logger = logging.getLogger(__name__)


class TelegramPollingWorker:
    """
    Background worker that fetches updates from Telegram using long-polling (getUpdates).
    This allows running the bot anywhere without needing a public domain, HTTPS, or ngrok.
    """

    def __init__(self, notifier: TelegramNotifier, handler: TelegramCommandHandler):
        self.notifier = notifier
        self.handler = handler
        self._stop_event = threading.Event()
        self._thread = None
        self.last_update_id = 0
        self.is_running = False

    def start(self):
        """Start the background polling worker."""
        if not self.notifier.is_configured():
            logger.warning("[TelegramPolling] TELEGRAM_BOT_TOKEN is not configured. Polling not started.")
            return

        if self._thread and self._thread.is_alive():
            logger.warning("[TelegramPolling] Worker is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="TelegramPollingWorker")
        self._thread.start()
        self.is_running = True
        logger.info("[TelegramPolling] Telegram long-polling worker started.")

    def stop(self):
        """Stop the background polling worker."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.is_running = False
        logger.info("[TelegramPolling] Telegram long-polling worker stopped.")

    def _answer_callback_query(self, callback_query_id: str):
        """Acknowledge a button click on Telegram."""
        if not self.notifier.is_configured() or not callback_query_id:
            return
        try:
            url = f"{self.notifier.base_url}/answerCallbackQuery"
            requests.post(url, json={"callback_query_id": callback_query_id}, timeout=5)
        except Exception:
            pass

    def _poll_loop(self):
        """Main loop fetching updates from Telegram."""
        logger.info("[TelegramPolling] Listening for Telegram messages...")

        while not self._stop_event.is_set():
            try:
                url = f"{self.notifier.base_url}/getUpdates"
                params = {
                    "offset": self.last_update_id + 1 if self.last_update_id else 0,
                    "timeout": 20,
                    "allowed_updates": ["message", "callback_query"]
                }

                # Use a slightly longer timeout than Telegram's internal timeout
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"[TelegramPolling] getUpdates HTTP {resp.status_code}: {resp.text}")
                    time.sleep(2)
                    continue

                data = resp.json()
                if not data.get("ok"):
                    logger.warning(f"[TelegramPolling] getUpdates failed: {data}")
                    time.sleep(3)
                    continue

                updates = data.get("result", [])
                for update in updates:
                    update_id = update.get("update_id", 0)
                    if update_id > self.last_update_id:
                        self.last_update_id = update_id

                    # 1. Process regular message
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
                            threading.Thread(
                                target=self._safe_handle_message,
                                args=(chat_id, text, user_name, chat_type),
                                daemon=True
                            ).start()

                    # 2. Process inline keyboard callback query (button clicks)
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb.get("id")
                        chat_id = cb.get("message", {}).get("chat", {}).get("id")
                        from_user = cb.get("from", {})
                        user_name = from_user.get("first_name", "")
                        data_text = cb.get("data", "")

                        self._answer_callback_query(cb_id)

                        if chat_id and data_text:
                            threading.Thread(
                                target=self._safe_handle_message,
                                args=(chat_id, data_text, user_name, "user"),
                                daemon=True
                            ).start()

            except requests.exceptions.Timeout:
                # Normal for long-polling when no updates arrived within timeout
                continue
            except requests.exceptions.ConnectionError:
                logger.warning("[TelegramPolling] Network connection dropped. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"[TelegramPolling] Unexpected loop error: {e}")
                time.sleep(3)

    def _safe_handle_message(self, chat_id, text, user_name, chat_type):
        """Execute message handler inside dedicated thread with error trapping."""
        try:
            self.handler.handle_message(
                chat_id=chat_id,
                text=text,
                user_name=user_name,
                chat_type=chat_type
            )
        except Exception as handle_err:
            logger.error(f"[TelegramPolling] Error handling message in thread: {handle_err}", exc_info=True)

