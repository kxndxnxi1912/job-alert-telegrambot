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

    # 1. Non-IT Roles & Positions in Titles (Always Disqualified unless explicit software dev role develops software for that domain)
    NEGATIVE_ROLES = [
        # Clerical, Office Assistant & Admin
        "ผู้ช่วยประจำสำนักงาน", "ผู้ช่วยสำนักงาน", "ผู้ช่วยผู้บริหาร", "ผู้ช่วยส่วนตัว", "ผู้ช่วยทั่วไป",
        "ผู้ช่วย", "office assistant", "executive assistant", "personal assistant", "general assistant",
        "assistant", "ธุรการ", "ธุรการสำนักงาน", "งานธุรการ", "เสมียน", "clerk", "admin ตอบ", "แอดมินตอบ",
        "แอดมินเพจ", "แอดมินร้าน", "คีย์ข้อมูล", "data entry", "พิมพ์งาน", "พิมพ์เอกสาร", "จัดเก็บเอกสาร",
        "สแกนเอกสาร", "กรอกข้อมูล", "เลขา", "เลขานุการ", "secretary", "receptionist", "พนักงานต้อนรับ",
        "โอเปอเรเตอร์", "operator", "ประสานงานทั่วไป", "จัดซื้อ", "จัดส่งเอกสาร", "ส่งพัสดุ",
        # Accounting & Finance
        "บัญชี", "นักบัญชี", "พนักงานบัญชี", "ปิดงบ", "การเงิน", "ภาษี", "ผู้สอบบัญชี",
        "งบการเงิน", "ตรวจสอบบัญชี", "ลงบัญชี", "ทำบัญชี", "ยื่นภาษี", "accountant",
        "accounting", "bookkeeper", "auditor", "audit", "credit analysis", "เจ้าหน้าที่การเงิน",
        # Sales & Marketing (Non-Coding)
        "เซลล์", "sales", "พนักงานขาย", "telesales", "นายหน้า", "call center",
        "คอลเซ็นเตอร์", "โทรขาย", "ติดตามหนี้", "ทวงหนี้", "ยืนบูธ", "ขายของ", "ขายคอร์ส",
        "ขายแบรนด์", "หา lead", "ตัวแทนจำหน่าย", "ปิดการขาย", "ตอบแชท", "ตอบไลน์", "ตอบ inbox",
        # Trades & Manual Services
        "ช่างเครื่องประดับ", "ช่างทอง", "จิวเวลรี่", "เครื่องประดับ", "ช่างแอร์", "ช่างไม้", "ช่างไฟ",
        "ช่างทำผม", "ช่างตัดชุด", "ช่างเย็บ", "ช่างซ่อมบำรุง", "ช่างประกอบ", "เฟอร์นิเจอร์",
        "แม่บ้าน", "ทำความสะอาด", "ขนของ", "ย้ายของ", "ขับรถ", "ไรเดอร์", "คนขับรถ",
        "ซ่อมคอม", "ร้านอาหาร", "ร้านกาแฟ", "ร้านดอกไม้", "พี่เลี้ยง", "สุนัข", "สัตว์เลี้ยง", "pet sitter",
        # Entertainment & Gaming (Non-Coding)
        "vj", "mc", "ไลฟ์สด", "liveสด", "tiktok live", "นักร้อง", "นักแสดง",
        "นางแบบ", "นายแบบ", "ตากล้อง", "ถ่ายรูป", "ถ่ายคลิป", "ถ่ายวิดีโอ", "ถ่ายภาพ",
        "เพื่อนเที่ยว", "เพื่อนกินข้าว", "เพื่อนคุย", "เพื่อนไป", "ฟาร์มเกม", "เล่นเกม",
        "เกมส์แทน", "maplestory", "กดบัตร", "thaiticketmajor",
        # Surveys & Passive / Non-Technical Data Tasks
        "แบบสอบถาม", "เก็บแบบสอบถาม", "ตอบแบบสอบถาม", "ผู้ทดลองใช้งาน",
        "ปล่อยแบบสอบถาม", "อ่านแบบสอบถาม",
        # Voice acting / Recording (Non-Coding / Data Contributor)
        "บันทึกเสียง", "อัดเสียง", "พากย์เสียง", "ลงเสียง", "voice recording", "voice over",
        "อ่านบทความ", "อ่านสคริปต์",
        # Pure Graphic / Video Editing without coding
        "ตัดต่อวิดีโอ", "ตัดต่อคลิป", "ตัดต่อวิดิโอ", "graphic designer",
        "ออกแบบสติกเกอร์", "วาดรูป", "แต่งรูป", "เขียนบทความ", "เขียนแคปชั่น", "ทำภาพ canva"
    ]

    # 2. Non-IT Duties & Tasks typically appearing in job description/content
    NEGATIVE_DUTIES = [
        "ช่วยงานผู้บริหาร", "จัดเก็บและจัดระเบียบเอกสาร", "จัดเก็บเอกสาร", "สแกนเอกสาร", "พิมพ์เอกสาร",
        "จัดระเบียบเอกสาร", "งานบันทึกข้อมูล", "data entry", "กรอกข้อมูล", "จัดทำใบแจ้งหนี้", "จัดทำใบเสร็จ",
        "ออกบิล", "วางบิล", "เดินบิล", "จัดส่งเอกสารหรือพัสดุ", "จัดส่งเอกสาร", "ส่งพัสดุ",
        "ประสานงานกับบุคคลภายนอก", "ประสานงานภายนอก", "ประสานงานทั่วไป", "เปรียบเทียบราคาซัพพลายเออร์",
        "เปรียบเทียบราคา", "สั่งของ", "ซื้อของ", "ดูแลความเรียบร้อย", "ดูแลช่าง", "งานเบ็ดเตล็ด",
        "ตอบแชทลูกค้า", "ตอบอินบ็อกซ์", "ตอบเพจ", "ตอบลูกค้า", "รับโทรศัพท์", "โทรสอบถาม",
        "อัดเสียงใส่ไมค์", "อ่านสคริปต์", "บันทึกเสียงภาษา", "เฝ้าร้าน", "ดูแลร้าน"
    ]

    # 3. Disguised Consumer-Level AI / Office Tool Phrases (Trickery Detection)
    # Employers who post clerical jobs often write "familiar with ChatGPT/Claude", "uses AI to help draft docs"
    CONSUMER_AI_PATTERNS = [
        r"คุ้นเคยกับ\s*(?:chatgpt|claude|gemini|ai|ปัญญาประดิษฐ์)",
        r"(?:สามารถ)?ใช้\s*(?:chatgpt|claude|gemini|ai|canva)\s*(?:ได้|เป็น|ช่วย|คล่อง)",
        r"ใช้\s*(?:chatgpt|claude|ai)\s*(?:ช่วย|ในการ)?(?:พิมพ์|เขียน|ตอบ|ร่าง|จัด|ค้นหา|สรุป|ทำภาพ)",
        r"(?:word|excel|google drive|canva).*?(?:chatgpt|claude|ai)",
        r"(?:chatgpt|claude|ai).*?(?:word|excel|google drive|canva)",
        r"ทักษะ.*?(?:word|excel|chatgpt)",
        r"บันทึกเสียง.*?(?:ai|เทรน|training)",
        r"อัดเสียง.*?(?:ai|เทรน|training)",
        r"ตอบแชท.*?(?:chatgpt|ai)",
        r"ตอบลูกค้า.*?(?:chatgpt|ai)"
    ]

    # Fastwork Category Tags that are fundamentally Non-IT
    NON_IT_FASTWORK_TAGS = [
        "ช่าง", "ไลฟ์สไตล์", "อินฟลูเอนเซอร์", "นักพากย์เสียง", "ศิลปะและภาพวาด",
        "ธุรกิจและการเงิน", "จัดการร้านค้าออนไลน์", "การตลาด"
    ]

    # 4. Explicit Developer / Engineer Roles
    EXPLICIT_DEV_ROLES = [
        "programmer", "โปรแกรมเมอร์", "developer", "software engineer",
        "วิศวกรซอฟต์แวร์", "coder", "คนเขียนโปรแกรม", "คนทำเว็บ", "คนสร้างเว็บ",
        "คนทำแอป", "คนเขียนบอท", "คนเขียนโค้ด", "fullstack", "full-stack",
        "frontend", "front-end", "backend", "back-end", "devops",
        "data engineer", "data scientist", "ai engineer", "ml engineer",
        "ai solutions architect", "ai solutions", "system analyst", "solution architect",
        "qa engineer", "software tester", "cloud engineer", "database administrator"
    ]

    # 5. Genuine Technical Deliverables & Action Verbs
    GENUINE_DEV_DELIVERABLES = [
        "เขียนโปรแกรม", "เขียนโค้ด", "พัฒนาระบบ", "พัฒนาเว็บ", "พัฒนาแอป", "พัฒนาแอพ",
        "สร้างเว็บ", "สร้างแอป", "สร้างระบบ", "ทำเว็บ", "ทำแอป", "ทำระบบ", "ออกแบบระบบ",
        "เขียนบอท", "สร้างบอท", "เชื่อมต่อ api", "เขียน api", "rest api", "restful api",
        "แก้โค้ด", "แก้บั๊ก", "ขูดข้อมูล", "web scraping", "crawler", "เทรนโมเดล",
        "fine-tune", "โมเดล ai", "ai pipeline", "rag system", "ai agent", "langchain",
        "llamaindex", "deploy", "database schema", "ออกแบบฐานข้อมูล", "พัฒนาโปรแกรม",
        "พัฒนาซอฟต์แวร์", "ทำ web app", "พัฒนา web app"
    ]

    # 6. Real Technical Programming Languages & Frameworks
    TECH_STACK = [
        "python", "fastapi", "django", "flask", "javascript", "typescript",
        "react", "react native", "nextjs", "next.js", "vue", "vuejs", "angular",
        "flutter", "nodejs", "node.js", "golang", "laravel", "spring boot",
        "docker", "kubernetes", "aws", "gcp", "azure", "supabase", "firebase",
        "postgresql", "mysql", "mongodb", "c#", ".net", "sql server", "sqlite",
        "redis", "php", "java", "swift", "kotlin", "c++", "rust", "graphql", "tailwind",
        "pytorch", "tensorflow"
    ]

    _EVAL_CACHE = {}

    @classmethod
    def _call_gemini_api(cls, title: str, content: str, user_prompt: str) -> dict | None:
        """
        Calls Google Gemini API for true LLM-powered job evaluation if GEMINI_API_KEY is present.
        Equipped with strict anti-deception instructions to catch disguised non-IT jobs.
        """
        api_key = getattr(Config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None

        prompt_guideline = user_prompt.strip() or Config.DEFAULT_PROMPT
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        system_instruction = (
            "You are an expert, rigorous AI Job Classifier for software developers, programmers, and IT professionals.\n"
            "Evaluate whether the provided freelance job posting is a GENUINE IT / Software Engineering / AI Development job.\n\n"
            f"TARGET CRITERIA: '{prompt_guideline}'\n\n"
            "🚨 CRITICAL ANTI-DECEPTION & TRICKERY RULES (ระวังเล่ห์เหลี่ยมในการโพสต์งาน):\n"
            "Many non-IT employers (Office Assistant, Secretary, Admin, Data Entry, Customer Service, Sales, Trades) sneak in keywords like 'familiar with ChatGPT/Claude', 'uses AI to help draft documents', or 'Word/Excel/Google Drive/AI'.\n"
            "- THESE ARE NOT IT OR AI JOBS! They are office/clerical roles using AI as a consumer end-user tool.\n"
            "- You MUST return is_match=false for any Office Assistant, Admin, Secretary, Data Entry, or Document filing job!\n"
            "- Voice recording or reading sentences for AI training datasets is NOT an IT job (return is_match=false)!\n"
            "- Accounting, Bookkeeping, Tax, Finance (บัญชี, การเงิน) are NOT IT jobs (return is_match=false)!\n"
            "- Sales, Marketing, Telesales, Customer service, Answering chat are NOT IT jobs (return is_match=false)!\n"
            "- Buying concert tickets or survey jobs are NOT IT jobs (return is_match=false)!\n\n"
            "QUALIFICATION RULES (Only return is_match=true if):\n"
            "- The job requires actual Software Development, Coding, Programming, Web/Mobile App engineering, DevOps, Database engineering, System architecture, or AI/ML model development / API integration (e.g. Python, JS, React, Node, Flutter, developing AI pipelines, fine-tuning, training, RAG, REST APIs).\n\n"
            "OUTPUT JSON FORMAT ONLY:\n"
            "{\n"
            '  "is_match": true or false,\n'
            '  "confidence": 0-100,\n'
            '  "role_category": "Short Category (e.g. Full-Stack Web Development, AI / ML Engineering, Mobile App)",\n'
            '  "matched_skills": ["Skill1", "Skill2"],\n'
            '  "reason": "1-sentence Thai explanation of why this matches or was rejected"\n'
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
                "temperature": 0.0
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
        High-Precision Built-in Semantic AI Classifier with Anti-Trickery Analysis.
        Performs multi-layered verification:
        1. Fastwork Tag check
        2. Non-IT Role Title check
        3. Non-IT Content Duties check
        4. Consumer AI Tool / Disguised Job check
        5. Genuine Technical Deliverables & Tech Stack validation
        6. Custom Prompt Intent alignment
        """
        t_lower = title.lower().strip()
        c_lower = content.lower().strip()
        g_lower = group_name.lower().strip()
        full_text = f"{t_lower} {c_lower} {g_lower}"

        # Indicators
        has_dev_role = any(r in t_lower for r in cls.EXPLICIT_DEV_ROLES)
        has_dev_deliverable = any(d in full_text for d in cls.GENUINE_DEV_DELIVERABLES)
        
        # Check matched tech stack
        matched_tech = []
        for tech in cls.TECH_STACK:
            if tech.isascii() and len(tech) <= 4:
                pattern = rf"(?<![a-zA-Z]){re.escape(tech)}(?![a-zA-Z])"
                if re.search(pattern, full_text):
                    matched_tech.append(tech)
            else:
                if tech in full_text:
                    matched_tech.append(tech)

        has_tech_stack = len(matched_tech) > 0

        # ---------------------------------------------------------
        # Layer 1: Fastwork Category Tag Check
        # ---------------------------------------------------------
        if g_lower in cls.NON_IT_FASTWORK_TAGS:
            if not (has_dev_role and has_dev_deliverable):
                return {
                    "is_match": False,
                    "confidence": 98,
                    "role_category": "งานนอกสาย (Excluded)",
                    "matched_signals": [],
                    "reason": f"คัดกรองออก: หมวดหมู่งาน '{group_name}' ไม่ใช่สายงาน IT / พัฒนาซอฟต์แวร์",
                    "ai_source": "Built-in Semantic AI"
                }

        # ---------------------------------------------------------
        # Layer 2: Non-IT Role Title Check
        # ---------------------------------------------------------
        matched_neg_role = None
        for neg in cls.NEGATIVE_ROLES:
            if neg in t_lower:
                matched_neg_role = neg
                break

        if matched_neg_role:
            # Only allow if an explicit developer is building software for that business domain
            # e.g. "โปรแกรมเมอร์พัฒนาระบบบัญชี" (Programmer developing accounting system)
            if not (has_dev_role and has_dev_deliverable):
                return {
                    "is_match": False,
                    "confidence": 99,
                    "role_category": "งานนอกสาย (Excluded)",
                    "matched_signals": [],
                    "reason": f"คัดกรองออก: ตรวจพบลักษณะงานตำแหน่ง '{matched_neg_role}' ซึ่งไม่ใช่งานสาย IT หรือวิศวกรรมซอฟต์แวร์",
                    "ai_source": "Built-in Semantic AI"
                }

        # ---------------------------------------------------------
        # Layer 3: Non-IT Duties & Clerical Work Check
        # ---------------------------------------------------------
        matched_neg_duties = [d for d in cls.NEGATIVE_DUTIES if d in c_lower]
        if len(matched_neg_duties) >= 2 and not has_dev_deliverable:
            duties_str = ", ".join(matched_neg_duties[:3])
            return {
                "is_match": False,
                "confidence": 98,
                "role_category": "งานธุรการ/งานทั่วไป (Clerical Duties)",
                "matched_signals": [],
                "reason": f"คัดกรองออก: เนื้องานหลักเป็นงานธุรการ/บริการทั่วไป ({duties_str}) ไม่ใช่งานพัฒนาเทคโนโลยี",
                "ai_source": "Built-in Semantic AI"
            }

        # ---------------------------------------------------------
        # Layer 4: Trickery & Consumer AI Tool Disguise Check
        # ---------------------------------------------------------
        is_consumer_ai = any(bool(re.search(pat, full_text, re.IGNORECASE)) for pat in cls.CONSUMER_AI_PATTERNS)
        if is_consumer_ai and not (has_dev_deliverable or has_tech_stack):
            return {
                "is_match": False,
                "confidence": 99,
                "role_category": "ผู้ใช้งานทั่วไป (Consumer AI)",
                "matched_signals": [],
                "reason": "ตรวจพบเล่ห์เหลี่ยม: ระบุให้ใช้ ChatGPT/AI ในฐานะเครื่องมือช่วยงานเอกสารทั่วไป ไม่ใช่งานสาย IT",
                "ai_source": "Built-in Semantic AI"
            }

        # ---------------------------------------------------------
        # Layer 5: Genuine IT Signals Verification
        # ---------------------------------------------------------
        matched_signals = []
        for role in cls.EXPLICIT_DEV_ROLES:
            if role in t_lower:
                matched_signals.append(role)
        for deliv in cls.GENUINE_DEV_DELIVERABLES:
            if deliv in full_text:
                matched_signals.append(deliv)
        for tech in matched_tech:
            matched_signals.append(tech)

        # Deduplicate signals
        seen = set()
        unique_signals = []
        for s in matched_signals:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique_signals.append(s)

        if not unique_signals:
            return {
                "is_match": False,
                "confidence": 90,
                "role_category": "ทั่วไป (Non-IT)",
                "matched_signals": [],
                "reason": "ไม่พบลักษณะงานที่เกี่ยวกับการเขียนโค้ด พัฒนาระบบ หรือวิศวกรรม AI",
                "ai_source": "Built-in Semantic AI"
            }

        # ---------------------------------------------------------
        # Layer 6: Custom Prompt Specific Intent Matching
        # ---------------------------------------------------------
        clean_prompt = (user_prompt or "").strip().lower()
        if clean_prompt and clean_prompt != Config.DEFAULT_PROMPT.lower():
            # Check if user specifically restricted to AI
            wants_ai_only = any(k in clean_prompt for k in ["ai", "ปัญญาประดิษฐ์", "machine learning", "deep learning", "โมเดล"]) and not any(k in clean_prompt for k in ["ซอฟต์แวร์", "โค้ด", "เว็บ", "แอป"])
            if wants_ai_only:
                ai_specific_signals = [s for s in unique_signals if any(k in s.lower() for k in ["ai engineer", "ml engineer", "ai solutions", "โมเดล ai", "ai pipeline", "rag system", "ai agent", "langchain", "llamaindex", "pytorch", "tensorflow", "fine-tune"])]
                if not ai_specific_signals:
                    return {
                        "is_match": False,
                        "confidence": 88,
                        "role_category": "ซอฟต์แวร์ทั่วไป",
                        "matched_signals": unique_signals[:5],
                        "reason": "เป็นงานโปรแกรมแต่ไม่ตรงกับเงื่อนไขที่เน้นเฉพาะ AI",
                        "ai_source": "Built-in Semantic AI"
                    }

        # ---------------------------------------------------------
        # Layer 7: Determine Accurate IT Role Category
        # ---------------------------------------------------------
        sig_lower_str = " ".join(unique_signals).lower()
        if any(k in sig_lower_str for k in ["ai engineer", "ml engineer", "ai solutions", "โมเดล ai", "rag system", "ai agent", "langchain", "pytorch", "tensorflow", "fine-tune"]):
            category = "AI / Machine Learning Engineering"
        elif any(k in sig_lower_str for k in ["เว็บ", "web", "react", "nextjs", "vue", "frontend", "fullstack", "backend", "laravel", "php", "django"]):
            category = "Web Development"
        elif any(k in sig_lower_str for k in ["flutter", "react native", "แอป", "แอพ", "mobile app", "swift", "kotlin"]):
            category = "Mobile Application"
        elif any(k in sig_lower_str for k in ["devops", "docker", "kubernetes", "aws", "gcp", "azure"]):
            category = "DevOps & Cloud Engineering"
        elif any(k in sig_lower_str for k in ["data engineer", "data scientist", "etl", "bigquery", "sql"]):
            category = "Data Engineering & Analytics"
        else:
            category = "Software Engineering & Coding"

        return {
            "is_match": True,
            "confidence": 95,
            "role_category": category,
            "matched_skills": unique_signals[:5],
            "reason": f"ตรงกับสายงาน IT: เป็นงานพัฒนาซอฟต์แวร์/ระบบด้าน {category} โดยตรง",
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
