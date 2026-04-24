"""
debug_url.py
============
ทดสอบ URL เดียวแบบ manual — เหมาะสำหรับ debug ก่อนปล่อยให้ n8n ใช้

วิธีใช้:
    python debug_url.py
    หรือตั้ง url= ใน .env แล้วรัน
"""

import os
import time
from dotenv import load_dotenv
from selenium_driver import (
    get_driver,
    check_login_status,
    login,
    open_apps_script_from_sheets,
    enable_chrome_v8,
)

load_dotenv()

email = os.getenv('GOOGLE_EMAIL')
password = os.getenv('GOOGLE_PASSWORD')
url = os.getenv('url') or os.getenv('SPREADSHEET_URL')

if not url:
    url = input('กรอก Google Sheets URL: ').strip()

if not url:
    print('❌ ไม่มี URL')
    exit(1)

print(f'🔗 URL: {url}')
print(f'📧 Email: {email}')

driver = get_driver(headless=False)  # headless=False เพื่อดูหน้าจอตอน debug

try:
    print('\n[1] ตรวจสอบ login status...')
    if not check_login_status(driver):
        if email and password:
            print('[1] ยังไม่ได้ login — กำลัง login...')
            login(driver, email, password)
        else:
            raise Exception('ยังไม่ได้ login และไม่มี credentials ใน .env')
    else:
        print('[1] ✅ Login อยู่แล้ว')

    print(f'\n[2] เปิด Sheets: {url}')
    print('[3] เปิด Apps Script...')
    open_apps_script_from_sheets(driver, url)
    print(f'    URL ปัจจุบัน: {driver.current_url}')

    print('\n[4] เปิด V8 runtime...')
    result = enable_chrome_v8(driver)
    print(f'    ผลลัพธ์: {result}')

    driver.save_screenshot('debug_final.png')
    print('\n✅ เสร็จสิ้น — ดู debug_final.png')

except Exception as e:
    print(f'\n❌ Error: {e}')
    try:
        driver.save_screenshot('debug_error.png')
        print('📸 บันทึก screenshot ไว้ที่ debug_error.png')
    except Exception:
        pass

finally:
    input('\nกด Enter เพื่อปิด Chrome...')
    driver.quit()