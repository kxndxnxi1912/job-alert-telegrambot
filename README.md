# 🤖 Telegram Job Alert Bot (Fastwork & Facebook Groups)

ระบบค้นหาและแจ้งเตือนงาน Freelance & IT แบบ Real-time ผ่าน **Telegram Bot**  
ดึงข้อมูลประกาศงานจาก **Fastwork.co** และ **Facebook Groups** ชุมชนไอที/โปรแกรมเมอร์ชั้นนำกว่า 15 กลุ่ม  
พร้อมระบบ **Prompt AI** ที่เข้าใจภาษาพูดธรรมชาติ และส่งการ์ดแจ้งเตือนพร้อมปุ่มกดลิงก์ (Inline Buttons)

---

## ⚡ ทำไมต้อง Telegram? (ข้อดีเหนือกว่า LINE OA)

| คุณสมบัติ | LINE Official Account | Telegram Bot (บอทนี้) |
| :--- | :--- | :--- |
| **โควต้าข้อความ Push** | จำกัด **300 ข้อความ/เดือน** (แพ็กเกจฟรี) | 🚀 **ฟรี 100% ไม่จำกัดจำนวน (Unlimited)** |
| **ความเร็วในการส่ง** | มี Rate Limit จำกัด | รวดเร็ว รองรับถึง ~30 ข้อความ/วินาที |
| **การเชื่อมต่อ** | ต้องมี Public HTTPS Webhook (เช่น ngrok) | **รันบนเครื่องได้เลย (Long Polling)** ไม่ต้องง้อ ngrok |
| **ปุ่มกดและรูปแบบ** | Flex Message JSON | ข้อความ HTML สวยงาม + ปุ่มกดเปิดดูงานทันที |
| **ค่าใช้จ่าย** | เสียเงินหากส่งเกิน 300 ข้อความ | **ฟรีตลอดชีพ** |

---

## 🚀 เริ่มต้นใช้งานใน 2 นาที (Quick Start)

### ขั้นตอนที่ 1: สร้างบอทบน Telegram (รับ Token)
1. เปิดแอป Telegram ค้นหาบอทชื่อ **`@BotFather`**
2. พิมพ์คำสั่ง:
   ```text
   /newbot
   ```
3. ตั้งชื่อบอท (Display Name) เช่น: `Fastwork Job Alert`
4. ตั้งชื่อผู้ใช้ของบอท (Username ต้องลงท้ายด้วย `bot`) เช่น: `my_fastwork_alert_bot`
5. คุณจะได้รับ **HTTP API Token** (ตัวอย่าง: `7123456789:AAH...`)

---

### ขั้นตอนที่ 2: ตั้งค่า `.env`
เปิดไฟล์ `.env` ในโฟลเดอร์นี้ แล้ววาง Token ที่ได้ลงไป:
```env
TELEGRAM_BOT_TOKEN=7123456789:AAH...your_token_here
TELEGRAM_MODE=polling
DATABASE_URL=sqlite:///jobs.db
POLL_INTERVAL_SECONDS=30
```

---

### ขั้นตอนที่ 3: ติดตั้ง Dependencies และรันบอท
```bash
# ติดตั้ง Library (หากยังไม่ได้ติดตั้ง)
pip install -r requirements.txt

# รันระบบบอท
python Main.py
```
> เมื่อรันแล้ว ระบบจะเริ่มทำงานทันที:
> 1. บันทึกและเชื่อมต่อฐานข้อมูล SQLite (`jobs.db`)
> 2. เริ่มต้นสแกนงานจาก Fastwork และ Facebook เบื้องหลังทุก ๆ 30 วินาที
> 3. เปิดระบบ Telegram Long Polling คอยรับคำสั่งแบบ Real-time

---

### ขั้นตอนที่ 4: เริ่มใช้งานบอทใน Telegram
1. เปิด Telegram แล้วเข้าไปที่บอทของคุณ
2. กดปุ่ม **`START`** หรือพิมพ์ `/start`
3. บอทจะลงทะเบียน `chat_id` ของคุณเข้าสู่ระบบรับแจ้งเตือนอัตโนมัติ!

---

## 💬 วิธีใช้งาน & คำสั่ง (Commands)

### 1. สั่งหางานด้วยภาษาธรรมชาติ (Prompt AI) 🌟
คุณสามารถพิมพ์บอกประเภทงานที่อยากได้เป็นภาษาพูดได้ทันที:
* *"ช่วยหางานด้านซอฟต์แวร์ และการทำ AI"*
* *"งานเขียนโค้ด หรือเขียนโปรแกรม"*
* *"หางานทำเว็บ React และ Node.js"*
* *"อยากได้งาน Mobile app Flutter ครับ"*
* *"มีงานเขียนโปรแกรม Python ไหม"*
* *"อยากได้งานกราฟิก หรือตัดต่อวิดีโอ"*

**การทำงาน:**
1. ระบบ AI จะวิเคราะห์คำสั่ง คัดกรองงานที่ยังไม่หมดอายุในรอบ 1 สัปดาห์มาส่งให้คุณดูทันทีเป็นตัวอย่าง 5 อันดับแรก
2. บันทึก Prompt นี้ไว้สำหรับส่งแจ้งเตือนงานใหม่ให้คุณอัตโนมัติในอนาคต (แยกประวัติการส่งรายบุคคล ไม่ส่งซ้ำ 100%)

---

### 2. คำสั่งควบคุมระบบ (Slash Commands)
| คำสั่ง | คำสั่งภาษาไทย | คำอธิบาย |
| :--- | :--- | :--- |
| `/start` | `เริ่ม` | เริ่มต้นใช้งานบอท และลงทะเบียนรับแจ้งเตือน |
| `/help` | `วิธีใช้`, `ช่วยเหลือ` | แสดงคู่มือการใช้งานและตัวอย่าง Prompt |
| `/status` | `สถานะ` | ตรวจสอบ Prompt ปัจจุบันของคุณ และสถิติของระบบ |
| `/clear` | `ล้างคำสั่ง` | รีเซ็ตคำสั่งค้นหากลับเป็นค่าเริ่มต้น (รับงาน Dev & AI ทุกประเภท) |
| `/test` | `ทดสอบ` | ส่งการ์ดแจ้งเตือนงานตัวอย่างพร้อมปุ่มกดมายังแชทของคุณ |
| `/groups` | `กลุ่ม` | ดูรายชื่อกลุ่ม Facebook ที่บอทติดตามอยู่ |
| `/stop` | `ยกเลิก` | ปิดการแจ้งเตือนงานในแชทนี้ชั่วคราว |
| `/subscribe` | `ติดตาม` | เปิดรับการแจ้งเตือนงานใหม่อีกครั้ง |

---

## 🛠️ โครงสร้างโปรเจกต์ (Project Structure)

```text
D:\PreTest\TelegramBotFwFB\
├── Main.py                      # จุดเริ่มต้นโปรแกรม (Flask + Worker + Polling)
├── config.py                    # ค่าคอนฟิกและการตั้งค่าระบบ
├── database.py                  # ระบบจัดการฐานข้อมูล SQLite/PostgreSQL (SQLAlchemy)
├── telegram_handler.py          # ตัวจัดการคำสั่งและ Prompt AI ของ Telegram
├── telegram_polling.py          # ระบบ Long Polling รับข้อความจาก Telegram แบบไม่ต้องใช้ ngrok
├── worker.py                    # Background Worker สแกนงาน Fastwork & Facebook
├── requirements.txt             # รายการ Library ที่ใช้งาน
├── .env                         # ไฟล์เก็บกุญแจลับและ Token
├── .env.example                 # ตัวอย่างไฟล์คอนฟิก
├── notifier/
│   ├── telegram_notifier.py     # ตัวจัดรูปแบบข้อความ HTML และส่งแจ้งเตือนผ่าน Telegram API
│   ├── prompt_analyzer.py       # ระบบ NLP วิเคราะห์ภาษาธรรมชาติและจับกลุ่มคำศัพท์ไอที
│   └── matcher.py               # ระบบจับคู่และให้คะแนนความเกี่ยวข้องของงาน
└── scrapers/
    ├── fastwork_scraper.py      # ดึงงานสดจาก Fastwork API (กรองงานไม่หมดอายุ 1 สัปดาห์)
    └── facebook_scraper.py      # ดึงโพสต์งานจากกลุ่ม Facebook
```

---

## 🌐 การนำขึ้น Cloud / Production (Railway / Render / VPS)
หากต้องการรันบอทบน Cloud ตลอด 24 ชม.:
1. สามารถใช้โหมด `polling` รันบน Background Worker ได้เลยโดยไม่ต้องเปิด Webhook Port
2. หรือหากต้องการเปิด Webhook สามารถตั้งค่า:
   ```env
   TELEGRAM_MODE=webhook
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook
   ```
   และสั่ง Set Webhook ไปยัง Telegram ได้ทันที
