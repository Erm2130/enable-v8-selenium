"""
app.py
======
Flask API รับ URL จาก n8n แล้วเปิด V8 runtime ใน Google Apps Script

Endpoints:
    POST /enable-v8   body: {"url": "https://docs.google.com/spreadsheets/d/..."}
    GET  /health      ตรวจสอบว่า server ทำงานอยู่

Headers ที่ต้องส่ง:
    X-API-Key: <API_KEY จาก .env>

วิธีรัน:
    python app.py
"""

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from selenium_driver import (
    get_driver,
    check_login_status,
    open_apps_script_from_sheets,
    enable_chrome_v8,
)

load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv('API_KEY', '')


# ─── Middleware: ตรวจสอบ API Key ──────────────────────────────────────────────

@app.before_request
def check_api_key():
    # ยกเว้น health check
    if request.path == '/health':
        return None
    if not API_KEY:
        return None  # ถ้าไม่ได้ตั้ง API_KEY ใน .env ให้ผ่านได้ (dev mode)
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/enable-v8', methods=['POST'])
def enable_v8():
    data = request.get_json(silent=True) or {}
    sheets_url = data.get('url', '').strip()

    if not sheets_url:
        return jsonify({'success': False, 'error': 'ไม่มี url ใน body'}), 400

    if 'docs.google.com/spreadsheets' not in sheets_url:
        return jsonify({'success': False, 'error': 'URL ต้องเป็น Google Sheets'}), 400

    driver = get_driver(headless=False)
    try:
        # ตรวจสอบ session
        if not check_login_status(driver):
            return jsonify({
                'success': False,
                'error': 'Session หมดอายุ — กรุณารัน login_once.py ที่เครื่อง server ใหม่',
                'action_required': 'relogin',
            }), 401

        # เปิด Apps Script
        open_apps_script_from_sheets(driver, sheets_url)

        # เปิด V8
        result = enable_chrome_v8(driver)

        return jsonify({
            'success': result['status'] == 'success',
            'status': result['status'],
            'message': result['message'],
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        driver.quit()


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f'🚀 Server รันที่ http://0.0.0.0:{port}')
    print(f'🔑 API Key: {"ตั้งแล้ว ✅" if API_KEY else "ไม่ได้ตั้ง ⚠️  (dev mode)"}')
    app.run(host='0.0.0.0', port=port, debug=False)