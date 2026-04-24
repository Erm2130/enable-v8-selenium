import os
import json
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

SESSION_FILE = 'session.json'
PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome-profile')
SAVE_SCREENSHOTS = os.getenv('SAVE_SCREENSHOTS', 'true').lower() == 'true'


def screenshot(driver, filename):
    if not SAVE_SCREENSHOTS:
        return
    try:
        driver.save_screenshot(filename)
    except Exception:
        pass


def get_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1280,900')
    options.add_argument('--profile-directory=Default')
    options.add_argument(f'--user-data-dir={PROFILE_PATH}')

    chromedriver_path = ChromeDriverManager().install()
    if os.name == 'nt' and not chromedriver_path.endswith('.exe'):
        chromedriver_path = os.path.join(os.path.dirname(chromedriver_path), 'chromedriver.exe')

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def save_session(driver):
    cookies = driver.get_cookies()
    with open(SESSION_FILE, 'w') as f:
        json.dump(cookies, f)
    print(f'[session] บันทึก {len(cookies)} cookies แล้ว')


def load_session(driver, domain='https://script.google.com'):
    if not os.path.exists(SESSION_FILE):
        return False
    try:
        driver.get(domain)
        with open(SESSION_FILE, 'r') as f:
            cookies = json.load(f)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        driver.refresh()
        return True
    except Exception:
        return False


def check_login_status(driver):
    """
    เช็ค session จาก cookie โดยตรง — ไม่ต้องเปิดหน้า accounts.google.com
    เร็วกว่าเดิมมาก เพราะไม่ต้องรอ redirect
    """
    try:
        # ต้องอยู่บน domain google.com ก่อนถึงจะอ่าน cookie ได้
        if 'google.com' not in driver.current_url:
            driver.get('https://accounts.google.com')
            WebDriverWait(driver, 10).until(
                lambda d: 'google.com' in d.current_url
            )

        cookies = {c['name'] for c in driver.get_cookies()}
        # Google ใช้ cookie เหล่านี้ยืนยัน session ที่ login แล้ว
        auth_cookies = {'SID', 'HSID', 'SSID', '__Secure-3PSID', 'LSID'}
        logged_in = bool(cookies & auth_cookies)
        print(f'[login] session: {"✅ login อยู่" if logged_in else "❌ ยังไม่ได้ login"}')
        return logged_in
    except Exception:
        return False


def login(driver, email, password):
    """Login ด้วย email/password — รองรับ 2FA โดยรอให้ทำ manual"""
    wait = WebDriverWait(driver, 20)
    driver.get('https://accounts.google.com/signin')
    screenshot(driver, '01-before-login.png')

    # รอ element พร้อม ไม่ sleep fixed
    try:
        wait.until(lambda d: (
            'myaccount.google.com' in d.current_url
            or d.find_elements(By.CSS_SELECTOR, 'input[type="email"], input[name="identifier"]')
        ))
    except TimeoutException:
        pass

    if 'myaccount.google.com' in driver.current_url:
        print('[login] Login อยู่แล้ว')
        return True

    if 'challenge' in driver.current_url:
        screenshot(driver, '02-2fa-required.png')
        raise Exception('ต้องทำ 2FA ด้วยตัวเองก่อน แล้วรัน login_once.py ใหม่')

    # กรอก email
    email_input = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input[type="email"], input[name="identifier"], input[autocomplete="username"]'
    )))
    screenshot(driver, '03-email-input.png')
    email_input.clear()
    email_input.send_keys(email)

    next_btn = wait.until(EC.element_to_be_clickable((By.ID, 'identifierNext')))
    next_btn.click()

    # กรอก password — รอ element พร้อม
    password_input = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input[type="password"], input[name="password"], input[autocomplete="current-password"]'
    )))
    password_input.clear()
    password_input.send_keys(password)

    next_btn = wait.until(EC.element_to_be_clickable((By.ID, 'passwordNext')))
    next_btn.click()

    screenshot(driver, '04-after-password.png')

    # รอผลลัพธ์ — login สำเร็จ หรือ 2FA
    wait.until(lambda d: (
        check_login_status(d)
        or any(x in d.current_url for x in ['challenge', 'totp', 'sms', '2sv'])
    ))

    # ถ้าเจอ 2FA — poll รอ user ทำเอง
    if any(x in driver.current_url for x in ['challenge', 'totp', 'sms', '2sv']):
        screenshot(driver, '05-2fa-page.png')
        print('\n[login] ⚠️  ต้องทำ 2FA — กรุณาทำบนหน้าต่าง Chrome ที่เปิดอยู่')
        print('[login] รอสูงสุด 2 นาที...')
        try:
            WebDriverWait(driver, 120).until(lambda d: check_login_status(d))
        except TimeoutException:
            raise Exception('หมดเวลารอ 2FA — ลองใหม่อีกครั้ง')

    if check_login_status(driver):
        save_session(driver)
        print('[login] ✅ Login สำเร็จ')
        return True

    raise Exception('Login ไม่สำเร็จ — ลอง manual ด้วย login_once.py')


def open_apps_script_from_sheets(driver, sheets_url):
    """เปิด Apps Script จาก Google Sheets URL"""
    wait = WebDriverWait(driver, 30)
    driver.get(sheets_url)

    # รอให้หน้าโหลด — ไม่ว่าจะสำเร็จหรือ error
    try:
        wait.until(lambda d: (
            # โหลดสำเร็จ
            d.find_elements(By.CSS_SELECTOR,
                '#docs-extensions-menu, [data-tooltip="Extensions"], [aria-label="Extensions"]')
            # หรือเจอหน้า error ต่างๆ
            or 'Sorry, unable to open' in d.page_source
            or 'accessdenied' in d.current_url.lower()
            or 'ServiceLogin' in d.current_url
        ))
    except TimeoutException:
        pass

    screenshot(driver, '10-sheets-loaded.png')

    # ❌ ไม่มีสิทธิ์
    if 'accessdenied' in driver.current_url.lower():
        raise Exception('ไม่มีสิทธิ์เข้าถึง sheet นี้ — ตรวจสอบว่าได้รับสิทธิ์แก้ไขแล้ว')

    # ❌ หน้า "Sorry, unable to open the file" — Sheet ID ผิดหรือถูกลบ
    if 'Sorry, unable to open' in driver.page_source or 'Page Not Found' in driver.title:
        raise Exception('ไม่พบ Sheet นี้ — URL อาจผิดหรือ Sheet ถูกลบไปแล้ว')

    # ❌ session หมด ถูก redirect ไปหน้า login
    if 'ServiceLogin' in driver.current_url or 'signin' in driver.current_url.lower():
        raise Exception('Session หมดอายุระหว่างใช้งาน — กรุณารัน login_once.py ใหม่')

    # หาปุ่ม Extensions
    extensions_selectors = [
        '#docs-extensions-menu',
        '[data-tooltip="Extensions"]',
        'button[aria-label*="Extensions"]',
        '[aria-label="Extensions"]',
    ]
    extensions_btn = None
    for selector in extensions_selectors:
        try:
            extensions_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            print(f'[apps-script] พบ Extensions button: {selector}')
            break
        except (NoSuchElementException, TimeoutException):
            continue

    if not extensions_btn:
        screenshot(driver, 'debug-no-extensions-btn.png')
        raise Exception('ไม่พบเมนู Extensions — Sheet อาจยังโหลดไม่เสร็จ')

    original_handles = driver.window_handles
    extensions_btn.click()

    try:
        # รอ dropdown แล้วคลิก Apps Script
        apps_script_link = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(), 'Apps Script')]")
        ))
        apps_script_link.click()

        # รอ tab ใหม่เปิด
        WebDriverWait(driver, 10).until(
            lambda d: len(d.window_handles) > len(original_handles)
        )
        new_tab = [h for h in driver.window_handles if h not in original_handles][0]
        driver.switch_to.window(new_tab)

        # รอ Apps Script โหลด
        WebDriverWait(driver, 15).until(
            lambda d: 'script.google.com' in d.current_url
        )
        screenshot(driver, '11-apps-script-loaded.png')
        print(f'[apps-script] ✅ เปิด Apps Script สำเร็จ: {driver.current_url}')

    except TimeoutException:
        # กรณีที่ไม่เปิด tab ใหม่ แต่ navigate ในหน้าเดิม
        if 'script.google.com' in driver.current_url:
            screenshot(driver, '11-apps-script-loaded.png')
            print(f'[apps-script] ✅ เปิด Apps Script สำเร็จ (same tab): {driver.current_url}')
            return
        screenshot(driver, 'debug-apps-script-click-failed.png')
        raise Exception('ไม่สามารถเปิด Apps Script ได้ — ลองรันใหม่')

    except Exception as e:
        screenshot(driver, 'debug-apps-script-click-failed.png')
        raise Exception(f'ไม่สามารถเปิด Apps Script ได้: {e}')


def enable_chrome_v8(driver):
    """เปิด Chrome V8 runtime ใน Apps Script settings"""
    current_url = driver.current_url

    if 'script.google.com' not in current_url:
        raise Exception('ไม่ได้อยู่ใน Apps Script editor')

    # ไปที่ settings page
    if '/edit' in current_url:
        settings_url = current_url.replace('/edit', '/settings')
    elif '/settings' not in current_url:
        settings_url = current_url.rstrip('/') + '/settings'
    else:
        settings_url = current_url

    driver.get(settings_url)

    # รอ checkbox โหลด แทน sleep fixed
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="checkbox"]'))
        )
    except TimeoutException:
        pass

    screenshot(driver, 'project-settings-page.png')

    # หา V8 checkbox
    v8_checkbox = None

    xpath_selectors = [
        "//input[@type='checkbox'][@id='i10']",
        "//input[@type='checkbox'][@id='i11']",
        "//input[@type='checkbox'][@id='i12']",
        "(//input[@type='checkbox'])[2]",
        "(//input[@type='checkbox'])[3]",
    ]
    for selector in xpath_selectors:
        try:
            checkboxes = driver.find_elements(By.XPATH, selector)
            if checkboxes:
                v8_checkbox = checkboxes[0]
                break
        except Exception:
            continue

    # fallback: หาจาก label text
    if not v8_checkbox:
        for cb in driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
            try:
                parent_text = cb.find_element(By.XPATH, '..').text.lower()
                if 'v8' in parent_text or 'chrome' in parent_text:
                    v8_checkbox = cb
                    break
            except Exception:
                continue

    if not v8_checkbox:
        screenshot(driver, 'no-v8-checkbox-found.png')
        return {'status': 'not_found', 'message': 'ไม่พบ V8 checkbox ใน settings'}

    screenshot(driver, 'v8-checkbox-found.png')
    is_checked = v8_checkbox.is_selected()
    print(f'[v8] สถานะปัจจุบัน: {"เปิดอยู่แล้ว ✅" if is_checked else "ปิดอยู่ — กำลังเปิด..."}')

    if not is_checked:
        try:
            v8_checkbox.click()
        except Exception:
            driver.execute_script("arguments[0].click();", v8_checkbox)

        # รอ checkbox state เปลี่ยน แทน sleep fixed
        try:
            WebDriverWait(driver, 5).until(lambda d: v8_checkbox.is_selected())
        except TimeoutException:
            pass

        screenshot(driver, 'after-enabling-v8.png')

    if v8_checkbox.is_selected():
        screenshot(driver, 'v8-enabled-success.png')
        return {'status': 'success', 'message': 'เปิด Chrome V8 runtime สำเร็จ'}
    else:
        screenshot(driver, 'v8-enable-failed.png')
        return {'status': 'failed', 'message': 'ไม่สามารถเปิดใช้งาน V8 runtime ได้'}