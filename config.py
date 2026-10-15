import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_MODE = os.getenv("TELEGRAM_MODE", "polling").strip().lower()  # "polling" or "webhook"
    TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "").strip()   # e.g. "https://your-domain.com/telegram/webhook"
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    DEFAULT_TELEGRAM_CHAT_ID = os.getenv("DEFAULT_TELEGRAM_CHAT_ID", "").strip()  # Optional fallback chat ID

    # Database Settings
    # Railway provides DATABASE_URL. If missing, fallback to local SQLite for development.
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///jobs.db").strip()
    
    # SQLAlchemy requires "postgresql+psycopg2://" when using psycopg2 driver
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
        elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Scraper & Worker Settings
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))  # default: 30 seconds (ultra-fast real-time)
    FASTWORK_ENABLED = os.getenv("FASTWORK_ENABLED", "true").lower() in ("true", "1", "yes")
    FACEBOOK_ENABLED = os.getenv("FACEBOOK_ENABLED", "true").lower() in ("true", "1", "yes")

    # Facebook Master Preset of major Thai developer & freelance groups
    DEFAULT_FB_GROUPS = [
        "thaiprogrammer",              # สมาคมโปรแกรมเมอร์ไทย
        "webdeveloperthailand",        # Web Developer Thailand
        "reactthailand",               # React Developer Thailand
        "flutterthailand",             # Flutter & Mobile Developer Thailand
        "pythonthailand",              # Python Developer Thailand
        "datasciencethailand",         # Data Science & AI Thailand
        "wordpressdeveloperthai",      # WordPress Developer Thailand
        "itjobthailand",               # งาน IT & Freelance Thailand
        "frontenddeveloperthailand",   # Frontend Developer Thailand
        "nodethailand",                # Node.js Thailand
        "vuejsthailand",               # Vue.js Thailand
        "golangthailand",              # Golang Thailand
        "programmersfreelance",        # ฟรีแลนซ์โปรแกรมเมอร์
        "androiddevthailand",          # Android Developer Thailand
        "iosdevthailand"               # iOS Developer Thailand
    ]

    # Facebook Settings
    _raw_fb_groups = os.getenv("FB_GROUP_IDS", "").strip()
    FB_GROUP_IDS = [g.strip() for g in _raw_fb_groups.split(",") if g.strip()] if _raw_fb_groups else DEFAULT_FB_GROUPS

    # Optional Facebook session cookie (e.g. "c_user=...; xs=...")
    FB_COOKIE = os.getenv("FB_COOKIE", "").strip()
    # Optional RSSBridge / RSS feed URLs for Facebook groups
    FB_RSS_URLS = [u.strip() for u in os.getenv("FB_RSS_URLS", "").split(",") if u.strip()]
    # Enable simulation demo data when no FB credentials exist
    FB_DEMO_FALLBACK = os.getenv("FB_DEMO_FALLBACK", "true").lower() in ("true", "1", "yes")

    # Server Port (default 8000 for Koyeb / reads $PORT for Railway/Render)
    PORT = int(os.getenv("PORT", "8000"))

    # Optional Google Gemini API Key for 100% LLM prompt reasoning
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    # Default AI Job Search Prompt for subscribers without custom prompt
    DEFAULT_PROMPT = os.getenv("DEFAULT_PROMPT", "งานเกี่ยวกับ AI, ซอฟต์แวร์, การเขียนโค้ด (Coding & AI Engineering)").strip()

    # Default Keywords preset
    DEFAULT_KEYWORDS = [
        # Web & Frontend/Backend
        "เขียนโปรแกรม",
        "โปรแกรมเมอร์",
        "โปรแกรม",
        "เว็บ",
        "web",
        "website",
        "web developer",
        "ทำเว็บ",
        "รับทำเว็บ",
        "wordpress",
        "frontend",
        "backend",
        "fullstack",
        "react",
        "vue",
        "angular",
        "nextjs",
        "node",
        "nodejs",
        # Languages & Frameworks
        "python",
        "golang",
        "php",
        "java",
        "c#",
        "c++",
        "django",
        "fastapi",
        "flask",
        "laravel",
        "spring",
        ".net",
        "rust",
        "ruby",
        # Mobile Apps
        "mobile app",
        "แอพ",
        "แอป",
        "แอพพลิเคชั่น",
        "flutter",
        "react native",
        "ios",
        "android",
        "swift",
        "kotlin",
        # AI, Data & Tech
        "ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "data science",
        "data analyst",
        "nlp",
        "computer vision",
        "chatbot",
        "gpt",
        "llm",
        "prompt",
        # Design & Media
        "ui",
        "ux",
        "figma",
        "graphic",
        "กราฟิก",
        "ตัดต่อ",
        "video editor",
        # General IT & QA
        "tester",
        "qa",
        "devops",
        "docker",
        "cloud",
        "aws",
        "api"
    ]
