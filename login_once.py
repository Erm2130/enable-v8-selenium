"""
login_once.py
=============
รันครั้งเดียวบนเครื่อง server เพื่อ login Google account
หลังจากนี้ chrome-profile/ จะเก็บ session ไว้ — ไม่ต้อง login ใหม่

วิธีใช้:
    python login_once.py

หมายเหตุ:
- ต้องรันบนเครื่องที่มีหน้าจอ (ไม่ headless) เพื่อทำ 2FA ได้
- ถ้า session หมดอายุ ให้รันไฟล์นี้ใหม่
"""

import os
import time
from dotenv import load_dotenv
from selenium_driver import get_driver, save_session
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

email = os.getenv('GOOGLE_EMAIL')
password = os.getenv('GOOGLE_PASSWORD')

if not email or not password:
    print('❌ ไม่พบ GOOGLE_EMAIL หรือ GOOGLE_PASSWORD ใน .env')
    exit(1)

print(f'🔐 กำลัง login ด้วย: {email}')
print('⚠️  หน้าต่าง Chrome จะเปิดขึ้น — ถ้ามี 2FA ให้ทำเองในหน้าต่างนั้น\n')

driver = get_driver(headless=False)
wait = WebDriverWait(driver, 20)


def is_logged_in():
    url = driver.current_url
    return (
        'myaccount.google.com' in url
        or 'accounts.google.com/b/' in url
        or 'support.google.com' in url
    )


def fast_login():
    driver.get('https://accounts.google.com/signin')

    # รอแค่ element พร้อม ไม่ sleep แบบ fixed
    wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'input[type="email"], input[name="identifier"]'
    )))

    if is_logged_in():
        print('✅ Login อยู่แล้ว (จาก Chrome Profile)')
        save_session(driver)
        return True

    # กรอก email
    email_input = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input[type="email"], input[name="identifier"]'
    )))
    email_input.clear()
    email_input.send_keys(email)

    next_btn = wait.until(EC.element_to_be_clickable((By.ID, 'identifierNext')))
    next_btn.click()

    # กรอก password — รอ element พร้อมแทน sleep
    password_input = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input[type="password"], input[autocomplete="current-password"]'
    )))
    password_input.clear()
    password_input.send_keys(password)

    next_btn = wait.until(EC.element_to_be_clickable((By.ID, 'passwordNext')))
    next_btn.click()

    # รอผลลัพธ์ — หน้า login สำเร็จ หรือ 2FA
    wait.until(lambda d: (
        is_logged_in()
        or any(x in d.current_url for x in ['challenge', 'totp', 'sms', '2sv', 'myaccount'])
    ))

    # ถ้าเจอ 2FA — poll รอ user ทำเอง แทน sleep fixed
    if any(x in driver.current_url for x in ['challenge', 'totp', 'sms', '2sv']):
        print('🔑 ต้องทำ 2FA — กรุณาทำบนหน้าต่าง Chrome')
        print('   รอสูงสุด 2 นาที...')
        try:
            WebDriverWait(driver, 120).until(lambda d: is_logged_in())
        except Exception:
            raise Exception('หมดเวลารอ 2FA — ลองใหม่อีกครั้ง')

    if is_logged_in():
        save_session(driver)
        return True

    raise Exception('Login ไม่สำเร็จ')


try:
    fast_login()
    print('✅ Login สำเร็จ! Session เก็บไว้ใน chrome-profile/ แล้ว')
    print('📌 ตอนนี้รัน app.py ได้เลย')
    print('🔒 ปิด Chrome อัตโนมัติ...')
    time.sleep(1)  # pause เล็กน้อยให้เห็น message

except Exception as e:
    print(f'\n❌ Error: {e}')
    input('กด Enter เพื่อปิด...')

finally:
    driver.quit()