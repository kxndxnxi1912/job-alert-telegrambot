import html
import logging
from config import Config
import database
from notifier.telegram_notifier import TelegramNotifier
from notifier.prompt_analyzer import PromptAnalyzer

logger = logging.getLogger(__name__)


def get_full_help_text() -> str:
    """Returns the comprehensive cheatsheet and guide of all bot commands."""
    return (
        "📖 <b>คู่มือวิธีใช้งาน Job Alert Bot (Telegram AI) 🤖</b>\n"
        "ระบบค้นหาและแจ้งเตือนงานอัตโนมัติด้วยคำสั่ง Prompt AI\n"
        "รวบรวมงานจาก Fastwork และ Facebook Groups (200+ งานล่าสุดในรอบ 1 สัปดาห์)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🌟 <b>1. วิธีสั่งค้นหางาน (พิมพ์บอก AI ได้ทันที)</b>\n"
        "พิมพ์บอกประเภทงานที่คุณต้องการเป็นภาษาพูดได้เลย เช่น:\n"
        "• <i>'ช่วยหางานด้านซอฟต์แวร์ และการทำ AI'</i>\n"
        "• <i>'งานเขียนโค้ด หรือเขียนโปรแกรม'</i>\n"
        "• <i>'หางานทำเว็บ React และ Node.js'</i>\n"
        "• <i>'อยากได้งาน Mobile app Flutter ครับ'</i>\n"
        "• <i>'มีงานเขียนโปรแกรม Python ไหม'</i>\n"
        "• <i>'อยากได้งานกราฟิก หรือตัดต่อวิดีโอ'</i>\n\n"
        "💡 <b>สิ่งที่ระบบจะทำ:</b>\n"
        "1. วิเคราะห์คำสั่ง และดึงงานสดที่ยังไม่หมดอายุในรอบ 1 สัปดาห์มาส่งให้คุณดูทันที\n"
        "2. บันทึก Prompt นี้ไว้คอยส่งแจ้งเตือนงานใหม่ให้คุณอัตโนมัติ (ไม่ส่งซ้ำ 100%)!\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>2. คำสั่งจัดการระบบ</b>\n"
        "• /status หรือ <b>'สถานะ'</b> : ดู Prompt ปัจจุบันของคุณ และสถิติระบบ\n"
        "• /clear หรือ <b>'ล้างคำสั่ง'</b> : รีเซ็ตคำสั่งค้นหากลับเป็นค่าเริ่มต้น\n"
        "• /groups หรือ <b>'กลุ่ม'</b> : ดูรายชื่อกลุ่ม Facebook ที่บอทติดตาม\n"
        "• /test หรือ <b>'ทดสอบ'</b> : ทดลองรับการ์ดแจ้งเตือนงานตัวอย่าง\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔔 <b>3. การตั้งค่าแจ้งเตือน</b>\n"
        "• ระบบเปิดรับแจ้งเตือนให้อัตโนมัติทันทีที่คุณกด /start\n"
        "• 🚀 <b>ข้อดีของ Telegram:</b> แจ้งเตือนได้ฟรี ไม่จำกัดจำนวนครั้งต่อเดือน!\n"
        "• /stop หรือ <b>'ยกเลิก'</b> : ปิดการแจ้งเตือนงานในแชทนี้\n"
        "• /subscribe หรือ <b>'ติดตาม'</b> : เปิดรับการแจ้งเตือนงานใหม่อีกครั้ง\n"
        "• /help หรือ <b>'วิธีใช้'</b> : ดูคู่มือคำสั่งนี้อีกครั้ง"
    )


class TelegramCommandHandler:
    """Processes incoming Telegram updates, commands, and natural language prompts."""

    def __init__(self, notifier: TelegramNotifier):
        self.notifier = notifier

    def _search_live_jobs(self, user_prompt: str = "") -> list[dict]:
        """Fetch current jobs from Fastwork & Facebook and evaluate using PromptAIEngine."""
        from scrapers.fastwork_scraper import FastworkScraper
        from scrapers.facebook_scraper import FacebookScraper
        from notifier.prompt_ai_engine import PromptAIEngine

        all_jobs = []
        try:
            fw_jobs = FastworkScraper().fetch_jobs(max_pages=3)
            all_jobs.extend(fw_jobs)
        except Exception as e:
            logger.warning(f"[TelegramHandler] Error fetching Fastwork for live search: {e}")

        try:
            fb_jobs = FacebookScraper().fetch_jobs()
            all_jobs.extend(fb_jobs)
        except Exception as e:
            logger.warning(f"[TelegramHandler] Error fetching Facebook for live search: {e}")

        matched_jobs = []
        for job in all_jobs:
            eval_res = PromptAIEngine.evaluate_job(job, user_prompt)
            if eval_res.get("is_match"):
                job_copy = dict(job)
                job_copy["ai_eval"] = eval_res
                job_copy["matched_keywords"] = eval_res.get("matched_skills") or eval_res.get("matched_signals") or []
                job_copy["score"] = eval_res.get("confidence", 90)
                matched_jobs.append(job_copy)

        # Sort highest confidence score first
        matched_jobs.sort(key=lambda j: j.get("score", 0), reverse=True)
        return matched_jobs

    def handle_message(self, chat_id: str | int, text: str, user_name: str = "", chat_type: str = "user"):
        """
        Main message dispatcher for Telegram Bot.
        """
        chat_id_str = str(chat_id)
        raw_text = (text or "").strip()
        lower_text = raw_text.lower()

        logger.info(f"[TelegramHandler] Received message from {chat_id_str} ({user_name}): '{raw_text}'")

        # Auto-subscribe subscriber on any incoming interaction if not exists
        database.add_subscriber(chat_id_str, target_type=chat_type)

        # 1. START / เริ่มต้น
        if lower_text in ("/start", "start", "เริ่ม", "เริ่มต้น"):
            welcome_text = (
                f"👋 สวัสดีครับคุณ <b>{html.escape(user_name or 'ผู้ใช้งาน')}</b>! ยินดีต้อนรับสู่ <b>Job Alert Bot (Telegram Edition)</b> 🚀\n\n"
                "ผมคือบอทช่วยค้นหาและแจ้งเตือนงาน Freelance & IT จาก <b>Fastwork</b> และ <b>Facebook Groups</b> แบบ Real-time ครับ\n\n"
                "⚡ <b>ข้อดีบน Telegram:</b> แจ้งเตือนงานได้ <u>ไม่จำกัดจำนวนครั้ง</u> (ไม่มีลิมิตโควต้าข้อความรายเดือน)!\n\n"
                "💡 <b>คุณสามารถเริ่มใช้งานได้ทันที</b> โดยการพิมพ์ประเภทงานที่ต้องการค้นหา เช่น:\n"
                "• <i>'ช่วยหางาน AI และ Data Science'</i>\n"
                "• <i>'อยากได้งานทำเว็บ React และ Python'</i>\n"
                "• <i>'งานเขียนโปรแกรม หรือ Mobile App'</i>\n\n"
                "หรือกดคำสั่งด่วนด้านล่างได้เลยครับ:"
            )
            quick_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📖 วิธีใช้งาน", "callback_data": "/help"},
                        {"text": "📊 สถานะระบบ", "callback_data": "/status"}
                    ],
                    [
                        {"text": "🧪 ทดสอบรับการ์ดงาน", "callback_data": "/test"},
                        {"text": "👥 กลุ่มที่ติดตาม", "callback_data": "/groups"}
                    ]
                ]
            }
            self.notifier.send_message(chat_id_str, welcome_text, reply_markup=quick_keyboard)
            return

        # 2. HELP / วิธีใช้
        if lower_text in ("/help", "help", "วิธีใช้", "ช่วยเหลือ", "คำสั่ง", "เมนู", "menu"):
            self.notifier.send_message(chat_id_str, get_full_help_text())
            return

        # 3. GROUPS / กลุ่ม
        if lower_text in ("/groups", "groups", "กลุ่ม", "รายชื่อกลุ่ม"):
            group_list = "\n".join([f"• facebook.com/groups/{g}" for g in Config.FB_GROUP_IDS])
            msg = (
                f"👥 <b>รายชื่อ Facebook Groups ที่บอทกำลังติดตาม ({len(Config.FB_GROUP_IDS)} กลุ่ม):</b>\n\n"
                f"{group_list}\n\n"
                "💼 รวมทั้งงานทั้งหมดจาก <b>Fastwork.co</b> ด้วยครับ!"
            )
            self.notifier.send_message(chat_id_str, msg)
            return

        # 4. STOP / UNSUBSCRIBE / ยกเลิก
        if lower_text in ("/stop", "stop", "ยกเลิก", "ปิดแจ้งเตือน", "unsub", "unsubscribe"):
            success, reply_msg = database.remove_subscriber(chat_id_str)
            self.notifier.send_message(chat_id_str, f"🔕 {reply_msg}\nหากต้องการเปิดใหม่เมื่อไหร่ เพียงพิมพ์ /subscribe หรือ 'ติดตาม' ได้ตลอดเวลาครับ")
            return

        # 5. SUBSCRIBE / ติดตาม
        if lower_text in ("/subscribe", "subscribe", "ติดตาม", "เปิดแจ้งเตือน", "sub"):
            success, reply_msg = database.add_subscriber(chat_id_str, target_type=chat_type)
            self.notifier.send_message(chat_id_str, f"🔔 {reply_msg}")
            return

        # 6. CLEAR / RESET PROMPT / ล้างคำสั่ง
        if lower_text in ("/clear", "clear", "/reset", "reset", "ล้างคำสั่ง", "รีเซ็ต", "ล้าง prompt", "reset prompt"):
            database.clear_user_prompt(chat_id_str)
            reply = (
                "🔄 <b>รีเซ็ตคำสั่งค้นหากลับเป็นค่าเริ่มต้นเรียบร้อยแล้วครับ!</b>\n\n"
                f"📌 <b>Prompt เริ่มต้น:</b> <i>'{Config.DEFAULT_PROMPT}'</i>\n"
                "(ครอบคลุมเฉพาะงานพัฒนาซอฟต์แวร์, ทำเว็บ, แอปพลิเคชัน, AI และงานเขียนโค้ดเท่านั้น โดยคัดกรองงานบัญชี/ธุรการ/งานทั่วไปออก 100%)\n\n"
                "💡 หากต้องการระบุประเภทงานใหม่ สามารถพิมพ์บอกบอทได้เลยครับ!"
            )
            self.notifier.send_message(chat_id_str, reply)
            return

        # 7. STATUS / สถานะ
        if lower_text in ("/status", "status", "สถานะ", "เช็ค", "info"):
            stats = database.get_stats()
            user_prompt = database.get_user_prompt(chat_id_str)
            ai_source = "Gemini LLM + Built-in Semantic AI" if getattr(Config, "GEMINI_API_KEY", "") else "High-Precision Prompt AI (Built-in)"
            if user_prompt:
                prompt_line = f"🎯 <b>Prompt ค้นหาของคุณ:</b>\n👉 <i>'{html.escape(user_prompt)}'</i>\n"
            else:
                prompt_line = f"🎯 <b>Prompt ค้นหาของคุณ:</b> <i>'{html.escape(Config.DEFAULT_PROMPT)}' (ค่าเริ่มต้น)</i>\n"

            status_msg = (
                "📊 <b>สถานะระบบ Job Alert Bot (Telegram Edition) 🟢</b>\n\n"
                f"• <b>ฐานข้อมูล:</b> {stats.get('database')}\n"
                f"• <b>ระบบคัดกรอง:</b> 🧠 <b>{ai_source} 100%</b>\n"
                f"• <b>ผู้รับการแจ้งเตือน:</b> {stats.get('subscribers_count')} รายการ\n"
                f"• <b>โควต้าข้อความ:</b> 🚀 <b>ไม่จำกัด (Unlimited Free)</b>\n"
                f"{prompt_line}\n"
                f"• <b>สถิติการแจ้งเตือนที่ผ่านมา:</b> รวม {stats.get('total_jobs')} งาน\n"
                f"  - จาก Fastwork: {stats.get('fastwork_jobs')} งาน\n"
                f"  - จาก Facebook: {stats.get('facebook_jobs')} งาน\n\n"
                "ระบบพร้อมสแกนประกาศงานด้วย Prompt AI แบบ Real-time คัดกรองงานตรงสาย 100% ครับ!"
            )
            self.notifier.send_message(chat_id_str, status_msg)
            return

        # 8. TEST / ทดสอบ
        if lower_text in ("/test", "test", "ทดสอบ", "ลองส่ง"):
            sample_job = {
                "source": "Fastwork",
                "group_name": "Web & Programming",
                "title": "Full-Stack Web Developer (React + Python FastAPI & AI)",
                "budget": "35,000 บาท",
                "content": "ต้องการฟรีแลนซ์พัฒนาระบบหลังบ้านและหน้าบ้านสำหรับระบบจัดการสินค้าและแดชบอร์ด AI มี API พร้อมเชื่อมต่อ สามารถเริ่มงานได้ทันที",
                "url": "https://fastwork.co",
                "posted_label": "🟢 ทดสอบระบบ",
                "ai_eval": {
                    "role_category": "Web & AI Development",
                    "matched_skills": ["React", "Python FastAPI", "AI Dashboard", "REST API"],
                    "reason": "ตรงกับ Prompt งานพัฒนา Web Application และเชื่อมต่อระบบ AI",
                    "ai_source": "Prompt AI Engine"
                }
            }
            sent = self.notifier.send_message(
                chat_id=chat_id_str,
                text=self.notifier.format_job_html(sample_job, ai_result=sample_job["ai_eval"]),
                reply_markup=self.notifier.create_inline_keyboard("https://fastwork.co")
            )
            if sent:
                self.notifier.send_message(chat_id_str, "🧪 <i>ส่งการ์ดแจ้งเตือนงานตัวอย่างแบบ Prompt AI ให้เรียบร้อยแล้วครับ!</i>")
            else:
                self.notifier.send_message(chat_id_str, "⚠️ ไม่สามารถส่งการ์ดทดสอบได้ กรุณาตรวจสอบสถานะ Bot Token")
            return

        # 9. GREETINGS / คำทักทาย
        if PromptAnalyzer.is_greeting(raw_text):
            greet_reply = (
                f"สวัสดีครับคุณ <b>{html.escape(user_name or 'ผู้ใช้งาน')}</b>! 😊\n"
                "ผมคือ <b>Job Alert Bot</b> พร้อมช่วยค้นหาและแจ้งเตือนงานจาก Fastwork & Facebook ให้คุณครับ\n\n"
                "💡 <b>ลองพิมพ์บอกงานที่อยากได้ได้เลยครับ เช่น:</b>\n"
                "• <i>'ช่วยหางาน AI หรือ Data'</i>\n"
                "• <i>'อยากได้งาน React และ Node.js'</i>\n"
                "• <i>'มีงานเขียนโปรแกรม Python ไหม'</i>\n\n"
                "หรือพิมพ์ <b>/help</b> เพื่อดูวิธีใช้งานทั้งหมดครับ"
            )
            self.notifier.send_message(chat_id_str, greet_reply)
            return

        # 10. NATURAL LANGUAGE PROMPT AI / การค้นหางาน
        from notifier.prompt_ai_engine import PromptAIEngine
        is_prompt = PromptAnalyzer.is_job_search_prompt(raw_text)
        if is_prompt or (chat_type == "user" and len(raw_text) >= 2):
            prompt_info = PromptAIEngine.analyze_user_prompt(raw_text)
            display_title = prompt_info.get("display_title", "งาน AI และซอฟต์แวร์")

            # Save user prompt
            database.save_user_prompt(chat_id_str, raw_text)

            # Inform user that prompt is saved and search is underway
            ack_msg = (
                "🎯 <b>บันทึกคำสั่งค้นหา Prompt AI เรียบร้อยแล้วครับ!</b>\n\n"
                f"📝 <b>คำสั่งของคุณ:</b> <i>'{html.escape(raw_text)}'</i>\n"
                f"🏷️ <b>หมวดหมู่เป้าหมาย:</b> <code>{html.escape(display_title)}</code>\n"
                "🛡️ <b>การคัดกรอง:</b> <i>ตัดงานบัญชี, ธุรการ, กราฟิก และงานทั่วไปออก 100%</i>\n\n"
                "🔎 <i>กำลังใช้ Prompt AI สแกนงานสดจาก Fastwork & Facebook กรุณารอสักครู่...</i>"
            )
            self.notifier.send_message(chat_id_str, ack_msg)

            # Live search matching jobs from past 1 week using PromptAIEngine
            matching_jobs = self._search_live_jobs(raw_text)

            if matching_jobs:
                top_jobs = matching_jobs[:5]  # Send top 5 best matches
                result_header = (
                    f"🎉 <b>พบ {len(matching_jobs)} งานที่ผ่านการคัดกรองด้วย Prompt AI!</b>\n"
                    f"ส่งตัวอย่าง <b>Top {len(top_jobs)}</b> งานที่น่าสนใจที่สุดให้ด้านล่างนี้ครับ:\n"
                    "━━━━━━━━━━━━━━━━━━━"
                )
                self.notifier.send_message(chat_id_str, result_header)

                # Send each top job as a rich card with clickable inline button
                for job in top_jobs:
                    job_html = self.notifier.format_job_html(job, ai_result=job.get("ai_eval"))
                    keyboard = self.notifier.create_inline_keyboard(job.get("url", ""))
                    self.notifier.send_message(chat_id_str, job_html, reply_markup=keyboard)
                    # Mark as delivered to avoid sending duplicate notification later
                    post_id = job.get("post_id")
                    if post_id:
                        database.record_subscriber_received_job(chat_id_str, post_id)

                footer_msg = (
                    "🔔 <b>ระบบจะคอยเฝ้าติดตามงานใหม่ด้วย Prompt AI ให้คุณตลอด 24 ชม.</b>\n"
                    "เมื่องานที่เกี่ยวกับการเขียนโค้ด ซอฟต์แวร์ หรือ AI ถูกโพสต์ บอทจะแจ้งเตือนให้ทันทีครับ!"
                )
                self.notifier.send_message(chat_id_str, footer_msg)
            else:
                empty_msg = (
                    "🔎 <b>ยังไม่พบงานที่ตรงกับเงื่อนไขในรอบ 1 สัปดาห์ที่ผ่านมาครับ</b>\n\n"
                    "📌 <i>บอทได้บันทึก Prompt นี้ไว้แล้ว ระบบจะคอยสแกนงานใหม่ให้ทันทีที่มีประกาศงานเข้ามาครับ!</i>\n\n"
                    "💡 หมวดหมู่ที่รองรับ: AI, Machine Learning, Web, Mobile App, Coding, DevOps"
                )
                self.notifier.send_message(chat_id_str, empty_msg)
            return

        # 11. UNKNOWN / DEFAULT FALLBACK
        fallback_msg = (
            f"🤖 ได้รับข้อความ <i>'{html.escape(raw_text)}'</i> เรียบร้อยครับ\n\n"
            "💡 หากคุณต้องการ <b>ค้นหาหรือตั้งแจ้งเตือนงาน</b> สามารถพิมพ์บอกประเภทงานเป็นภาษาธรรมชาติได้เลย เช่น:\n"
            "• <i>'ช่วยหางาน AI หรือ Python'</i>\n"
            "• <i>'อยากได้งานทำเว็บ React'</i>\n"
            "• <i>'งานเขียนโค้ด Mobile App'</i>\n\n"
            "หรือพิมพ์ <b>/help</b> เพื่อดูคู่มือคำสั่งทั้งหมดครับ"
        )
        self.notifier.send_message(chat_id_str, fallback_msg)
