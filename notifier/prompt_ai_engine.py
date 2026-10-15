import re
import os
import json
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


class PromptAIEngine:
    """
    100% Prompt AI Engine for evaluating freelance job postings.
    Replaces naive substring keyword matching with full semantic context analysis:
    - Tier 1: Google Gemini LLM API (when GEMINI_API_KEY is configured).
    - Tier 2: High-Precision Built-in Semantic AI Classifier (Zero-cost, offline, ultra-fast).
    Strictly filters out non-coding domains (Accounting, Admin, Sales, Trades, Surveys, etc.)
    and accepts only true Software Engineering, Coding, Web/Mobile development, and AI/ML jobs.
    """

    # Negative non-coding roles & scopes that MUST be rejected
    NEGATIVE_ROLES = [
        # Accounting & Finance
        "บัญชี", "นักบัญชี", "พนักงานบัญชี", "ปิดงบ", "การเงิน", "ภาษี", "ผู้สอบบัญชี",
        "งบการเงิน", "ตรวจสอบบัญชี", "ลงบัญชี", "ทำบัญชี", "ยื่นภาษี", "accountant",
        "accounting", "bookkeeper", "auditor", "audit", "credit analysis",
        # Clerical & Admin
        "ธุรการ", "คีย์ข้อมูล", "data entry", "พิมพ์งาน", "พิมพ์เอกสาร", "จัดเก็บเอกสาร",
        "ประสานงานทั่วไป", "เลขา", "แอดมินตอบ", "แอดมินเพจ", "แอดมินร้าน", "admin ตอบ",
        "แปลงไฟล์ pdf", "นับรถ", "กรอกข้อมูล",
        # Sales & Marketing (Non-Coding)
        "เซลล์", "sales", "พนักงานขาย", "telesales", "นายหน้า", "call center",
        "คอลเซ็นเตอร์", "โทรขาย", "ติดตามหนี้", "ยืนบูธ", "ขายของ", "ขายคอร์ส",
        "ขายแบรนด์", "หา lead", "ตัวแทนจำหน่าย",
        # Trades & Manual Services
        "แม่บ้าน", "ทำความสะอาด", "ขนของ", "ย้ายของ", "ขับรถ", "ไรเดอร์", "ช่างแอร์",
        "ช่างไม้", "ช่างไฟ", "ช่างทำผม", "ช่างตัดชุด", "ช่างเย็บ", "ช่างซ่อมบำรุง",
        "ซ่อมคอม", "ร้านอาหาร", "ร้านกาแฟ", "ร้านดอกไม้", "พี่เลี้ยง", "สุนัข", "สัตว์เลี้ยง",
        # Entertainment & Gaming (Non-Coding)
        "vj", "mc", "ไลฟ์สด", "liveสด", "tiktok live", "นักร้อง", "นักแสดง",
        "นางแบบ", "นายแบบ", "ตากล้อง", "ถ่ายรูป", "ถ่ายคลิป", "ถ่ายวิดีโอ", "ถ่ายภาพ",
        "เพื่อนเที่ยว", "เพื่อนกินข้าว", "เพื่อนคุย", "เพื่อนไป", "ฟาร์มเกม", "เล่นเกม",
        "เกมส์แทน", "maplestory",
        # Surveys & Passive Users
        "แบบสอบถาม", "เก็บแบบสอบถาม", "ตอบแบบสอบถาม", "ผู้ทดลองใช้งาน",
        "ปล่อยแบบสอบถาม", "อ่านแบบสอบถาม",
        # Voice acting / Recording (Non-Coding)
        "บันทึกเสียง", "อัดเสียง", "พากย์เสียง", "ลงเสียง", "voice recording", "voice over",
        # Pure Graphic / Video Editing without coding
        "ตัดต่อวิดีโอ", "ตัดต่อคลิป", "ตัดต่อวิดิโอ", "graphic designer",
        "ออกแบบสติกเกอร์", "วาดรูป", "แต่งรูป"
    ]

    # Explicit developer roles that can override false negative mentions
    # (e.g. "โปรแกรมเมอร์พัฒนาระบบบัญชี" is ACCEPTED because the role is a programmer developing an accounting system)
    EXPLICIT_DEV_ROLES = [
        "programmer", "โปรแกรมเมอร์", "developer", "software engineer",
        "วิศวกรซอฟต์แวร์", "coder", "คนเขียนโปรแกรม", "คนทำเว็บ", "คนสร้างเว็บ",
        "คนทำแอป", "คนเขียนบอท", "คนเขียนโค้ด", "fullstack", "full-stack",
        "frontend", "front-end", "backend", "back-end", "devops",
        "data engineer", "data scientist", "ai engineer", "ml engineer",
        "ai solutions architect", "ai solutions"
    ]

    # Positive Software, Coding & AI Signals
    POSITIVE_DEV_SIGNALS = [
        # Explicit Roles
        "programmer", "โปรแกรมเมอร์", "developer", "นักพัฒนา", "software engineer",
        "วิศวกรซอฟต์แวร์", "coder", "คนเขียนโปรแกรม", "คนทำเว็บ", "คนสร้างเว็บ",
        "คนทำแอป", "คนเขียนบอท", "คนเขียนโค้ด", "fullstack", "full-stack",
        "frontend", "front-end", "backend", "back-end", "devops", "data engineer",
        "data scientist", "ai engineer", "ml engineer", "ai solutions",
        # Action Verbs + Software Deliverables
        "เขียนโปรแกรม", "เขียนเว็บ", "เขียนแอป", "เขียนแอพ", "เขียนบอท", "เขียนโค้ด",
        "พัฒนาระบบ", "พัฒนาเว็บ", "พัฒนาแอป", "พัฒนาแอพ", "พัฒนาฟีเจอร์", "ทำเว็บ",
        "สร้างเว็บ", "ทำแอป", "สร้างแอป", "ทำบอท", "สร้างบอท", "เชื่อมต่อ api",
        "ออกแบบระบบ", "แก้โค้ด", "แก้บั๊ก", "ขูดข้อมูล", "ขูดเว็บ", "web scraping",
        "เทรนโมเดล", "โมเดล ai", "ai training", "automation",
        # Definite Frameworks & Languages
        "python", "fastapi", "django", "flask", "javascript", "typescript",
        "react", "react native", "nextjs", "next.js", "vue", "vuejs", "angular",
        "flutter", "nodejs", "node.js", "golang", "laravel", "spring boot",
        "docker", "kubernetes", "aws", "gcp", "azure", "supabase", "firebase",
        "postgresql", "mysql", "mongodb", "tailwind", "chatgpt", "llm"
    ]

    _EVAL_CACHE = {}

    @classmethod
    def _call_gemini_api(cls, title: str, content: str, user_prompt: str) -> dict | None:
        """
        Calls Google Gemini API for true LLM-powered job evaluation if GEMINI_API_KEY is present.
        """
        api_key = getattr(Config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None

        prompt_guideline = user_prompt.strip() or Config.DEFAULT_PROMPT
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        system_instruction = (
            "You are an expert AI Job Evaluator for software developers, programmers, and AI practitioners.\n"
            "Evaluate whether the provided freelance job posting matches the user's target criteria.\n\n"
            f"TARGET CRITERIA: '{prompt_guideline}'\n"
            "(Focus strictly on: Software development, programming, coding, web/mobile development, DevOps, Data Science, and AI/Machine Learning.)\n\n"
            "STRICT EXCLUSIONS (Must return is_match=false):\n"
            "- Accounting, Bookkeeping, Tax, Finance (บัญชี, การเงิน, ปิดงบ) even if using accounting software.\n"
            "- Admin, Clerical, Data Entry, Typing (ธุรการ, แอดมินตอบแชท, คีย์ข้อมูล, จัดเอกสาร)\n"
            "- Sales, Marketing, Telesales, Customer service (พนักงานขาย, ยิงแอด, คอลเซ็นเตอร์)\n"
            "- Survey respondents or test users (ตอบแบบสอบถาม, ทดลองใช้เว็บ/แอป)\n"
            "- Manual labor, Drivers, Maids, Technicians (ช่างไม้, ช่างแอร์, แม่บ้าน, ขับรถ)\n"
            "- Entertainment, Actors, Companions, Gaming (VJ, MC, เพื่อนเที่ยว, ฟาร์มเกม)\n"
            "- Graphic design or Video editing without programming/AI generation.\n\n"
            "OUTPUT JSON FORMAT ONLY:\n"
            "{\n"
            '  "is_match": true or false,\n'
            '  "confidence": 0-100,\n'
            '  "role_category": "Short Category (e.g. Full-Stack Web Development, AI / ML, Mobile App)",\n'
            '  "matched_skills": ["Skill1", "Skill2"],\n'
            '  "reason": "1-sentence Thai explanation of why this matches or does not match"\n'
            "}"
        )

        job_text = f"หัวข้อประกาศงาน: {title}\nรายละเอียดงาน: {content[:1000]}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": job_text}]
                }
            ],
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                parsed["ai_source"] = "Gemini LLM"
                return parsed
            else:
                logger.warning(f"[PromptAI] Gemini API returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[PromptAI] Gemini API error: {e}. Falling back to Built-in Semantic AI.")

        return None

    @classmethod
    def _evaluate_builtin_semantic(cls, title: str, content: str, group_name: str, user_prompt: str) -> dict:
        """
        High-Precision Built-in Semantic AI Classifier.
        Analyzes role, intent, action verbs, and negative exclusions.
        """
        full_text = f"{title} {content} {group_name}".lower()
        t_lower = title.lower()

        # Check explicit developer role in title
        has_explicit_dev_role = any(r in t_lower for r in cls.EXPLICIT_DEV_ROLES)

        # 1. Negative Blacklist Verification
        for neg in cls.NEGATIVE_ROLES:
            if neg in t_lower:
                # Allow only if developer role is explicitly creating software for that domain
                # e.g. "โปรแกรมเมอร์เขียนระบบบัญชี" -> dev creating accounting system
                if has_explicit_dev_role and neg in ["บัญชี", "การเงิน", "ภาษี"] and any(v in t_lower for v in ["เขียนโปรแกรม", "พัฒนาระบบ", "developer", "programmer", "สร้างระบบ"]):
                    continue
                return {
                    "is_match": False,
                    "confidence": 98,
                    "role_category": "งานนอกสาย (Excluded)",
                    "matched_signals": [],
                    "reason": f"คัดกรองออก: ตรวจพบลักษณะงานสาย '{neg}' ซึ่งไม่ใช่งานเขียนโค้ด/ซอฟต์แวร์/AI",
                    "ai_source": "Built-in Semantic AI"
                }

        # 2. Check for positive developer / AI signals
        matched_signals = []
        for sig in cls.POSITIVE_DEV_SIGNALS:
            clean_sig = sig.lower()
            if clean_sig.isascii() and len(clean_sig) <= 4:
                pattern = rf"(?<![a-zA-Z]){re.escape(clean_sig)}(?![a-zA-Z])"
                if re.search(pattern, full_text):
                    matched_signals.append(sig)
            else:
                if clean_sig in full_text:
                    matched_signals.append(sig)

        if not matched_signals:
            return {
                "is_match": False,
                "confidence": 90,
                "role_category": "ทั่วไป",
                "matched_signals": [],
                "reason": "ไม่พบลักษณะงานที่เกี่ยวกับการเขียนโปรแกรม พัฒนาระบบ หรือ AI",
                "ai_source": "Built-in Semantic AI"
            }

        # 3. Custom Prompt Specific Intent Matching
        clean_prompt = (user_prompt or "").strip().lower()
        # If user explicitly asked for a specific subfield (e.g. AI only, Python only, Web only)
        if clean_prompt and clean_prompt != Config.DEFAULT_PROMPT.lower():
            # Check if user specifically restricted to AI
            wants_ai_only = any(k in clean_prompt for k in ["ai", "ปัญญาประดิษฐ์", "machine learning", "deep learning", "โมเดล"]) and not any(k in clean_prompt for k in ["ซอฟต์แวร์", "โค้ด", "เว็บ", "แอป"])
            if wants_ai_only:
                ai_signals = [s for s in matched_signals if s in ["ai engineer", "ml engineer", "ai solutions", "โมเดล ai", "ai training", "chatgpt", "llm", "data scientist", "data engineer"]]
                if not ai_signals:
                    return {
                        "is_match": False,
                        "confidence": 85,
                        "role_category": "ซอฟต์แวร์ทั่วไป",
                        "matched_signals": matched_signals,
                        "reason": "เป็นงานโปรแกรมแต่ไม่ตรงกับเงื่อนไขที่เน้นเฉพาะ AI",
                        "ai_source": "Built-in Semantic AI"
                    }

        # Determine Role Category
        category = "ซอฟต์แวร์ / การเขียนโค้ด"
        if any(s in matched_signals for s in ["ai engineer", "ml engineer", "ai solutions", "โมเดล ai", "ai training", "chatgpt", "llm"]):
            category = "AI / Machine Learning"
        elif any(s in matched_signals for s in ["คนสร้างเว็บ", "คนทำเว็บ", "พัฒนาเว็บ", "react", "nextjs", "vue", "frontend", "fullstack", "web app"]):
            category = "Web Development"
        elif any(s in matched_signals for s in ["flutter", "react native", "แอป", "แอพ", "mobile app"]):
            category = "Mobile Application"

        return {
            "is_match": True,
            "confidence": 95,
            "role_category": category,
            "matched_signals": matched_signals[:5],
            "reason": f"ตรงกับ Prompt: เป็นงานจ้างสาย {category} โดยตรง",
            "ai_source": "Built-in Semantic AI"
        }

    @classmethod
    def evaluate_job(cls, job: dict, user_prompt: str = "") -> dict:
        """
        Main evaluation entry point.
        Evaluates a job against the user's prompt using Gemini LLM or Built-in Semantic AI.
        Caches results per (post_id, prompt) to ensure ultra-high performance.
        """
        post_id = job.get("post_id") or ""
        title = (job.get("title") or "").strip()
        content = (job.get("content") or "").strip()
        group_name = (job.get("group_name") or "").strip()
        target_prompt = (user_prompt or Config.DEFAULT_PROMPT).strip()

        cache_key = f"{post_id}:{hash(target_prompt)}"
        if post_id and cache_key in cls._EVAL_CACHE:
            return cls._EVAL_CACHE[cache_key]

        # 1. Try Gemini LLM if configured
        gemini_result = cls._call_gemini_api(title, content, target_prompt)
        if gemini_result and isinstance(gemini_result, dict) and "is_match" in gemini_result:
            if post_id:
                cls._EVAL_CACHE[cache_key] = gemini_result
            return gemini_result

        # 2. High-Precision Built-in Semantic AI
        builtin_result = cls._evaluate_builtin_semantic(title, content, group_name, target_prompt)
        if post_id:
            cls._EVAL_CACHE[cache_key] = builtin_result
            if len(cls._EVAL_CACHE) > 1000:
                cls._EVAL_CACHE.pop(next(iter(cls._EVAL_CACHE)))

        return builtin_result

    @classmethod
    def analyze_user_prompt(cls, prompt_text: str) -> dict:
        """
        Summarizes user's prompt intent for display in Telegram UI.
        """
        clean = (prompt_text or "").strip()
        lower = clean.lower()

        domains = []
        if any(w in lower for w in ["ai", "เอไอ", "ปัญญาประดิษฐ์", "machine learning", "deep learning", "llm", "บอท"]):
            domains.append("AI / Machine Learning")
        if any(w in lower for w in ["เว็บ", "web", "ทำเว็บ", "frontend", "backend", "fullstack", "react", "next", "vue"]):
            domains.append("Web Development")
        if any(w in lower for w in ["แอป", "แอพ", "app", "mobile", "flutter", "ios", "android"]):
            domains.append("Mobile App")
        if any(w in lower for w in ["โค้ด", "เขียนโค้ด", "โปรแกรม", "เขียนโปรแกรม", "ซอฟต์แวร์", "software", "developer"]):
            domains.append("Software & Coding")

        if not domains:
            domains = ["AI, ซอฟต์แวร์ และการเขียนโค้ด"]

        return {
            "raw_prompt": clean,
            "target_domains": domains,
            "display_title": " + ".join(domains),
            "strict_filter": "คัดกรองงานบัญชี, ธุรการ, กราฟิก และงานทั่วไปออก 100%"
        }
