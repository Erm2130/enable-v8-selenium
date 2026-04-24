# Enable V8 Selenium Bot

ระบบเปิด Chrome V8 Runtime ใน Google Apps Script อัตโนมัติผ่าน Telegram Bot + n8n

---

## Requirements

- Python 3.10+
- Google Chrome (ติดตั้งแล้ว)
- n8n instance
- Telegram Bot token

---

## Setup

```bash
# 1. Clone และติดตั้ง dependencies
pip install -r requirements.txt

# 2. สร้างไฟล์ .env
cp .env.example .env
```

แก้ `.env` ให้ครบ:

```env
GOOGLE_EMAIL=อีเมลที่มีสิทธิ์แก้ไข Sheet ทุกบอร์ด
GOOGLE_PASSWORD=รหัสผ่าน
API_KEY=รหัสลับสำหรับ n8n (ตั้งเองได้อะไรก็ได้)
SAVE_SCREENSHOTS=false
```

---

## การรันครั้งแรก

**Login Google (ทำครั้งเดียว)**

```bash
python login_once.py
```

- Chrome จะเปิดขึ้น — ถ้ามี 2FA ให้ทำเองในหน้าต่างนั้น
- Login สำเร็จ Chrome ปิดอัตโนมัติ
- Session เก็บไว้ใน `chrome-profile/` — ใช้ได้ประมาณ 2-4 สัปดาห์

**รัน API Server**

```bash
python app.py
```

---

## Endpoints

```
GET  /health        — ตรวจสอบ server
POST /enable-v8     — เปิด V8 runtime

Header: X-API-Key: <ค่า API_KEY ใน .env>
Body:   {"url": "https://docs.google.com/spreadsheets/d/.../edit"}
```

**Response:**

```json
// สำเร็จ
{"success": true, "status": "success", "message": "เปิด Chrome V8 runtime สำเร็จ"}

// Session หมด → รัน login_once.py ใหม่
{"success": false, "action_required": "relogin"}

// URL ผิด / ไม่มีสิทธิ์
{"success": false, "error": "..."}
```

---

## เชื่อมต่อ n8n

ใน HTTP Request node:

| Field | Value |
|---|---|
| Method | POST |
| URL | `http://your-server:5000/enable-v8` |
| Header | `X-API-Key: <API_KEY>` |
| Body | `{"url": "{{ $json.message.text }}"}` |

> ถ้าใช้ Ngrok ระหว่างทดสอบ: `ngrok http 5000` แล้วเปลี่ยน URL เป็น ngrok URL

---

## Error ที่พบบ่อย

| Error | สาเหตุ | วิธีแก้ |
|---|---|---|
| `401 Unauthorized` | API Key ผิด | เช็ค header `X-API-Key` |
| `action_required: relogin` | Session หมด | `python login_once.py` |
| `ไม่พบ Sheet นี้` | URL ผิด / Sheet ถูกลบ | ตรวจสอบ URL |
| `ไม่มีสิทธิ์เข้าถึง` | Email ไม่มีสิทธิ์ edit | Share Sheet ให้ email ใน .env |
| `ไม่พบเมนู Extensions` | Sheet โหลดไม่เสร็จ / format ผิด | ส่ง URL ใหม่ |

---

## ไฟล์ที่ห้าม commit

```
.env
chrome-profile/
session.json
*.png
__pycache__/
```

> Session ใน `chrome-profile/` เทียบเท่ากับการล็อคอิน Google — อย่าแชร์ให้ใคร
