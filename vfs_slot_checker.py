import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from twilio.rest import Client
from datetime import datetime
import os
import traceback

# ─────────────────────────────────────────
#  KONFİQURASİYA
# ─────────────────────────────────────────
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
FROM_WHATSAPP = os.environ.get("FROM_WHATSAPP", "whatsapp:+14155238886")
TO_WHATSAPP   = os.environ["TO_WHATSAPP"]

VFS_EMAIL    = os.environ["VFS_EMAIL"]
VFS_PASSWORD = os.environ["VFS_PASSWORD"]

LOGIN_URL      = "https://visa.vfsglobal.com/aze/en/ita/login"
DASHBOARD_URL  = "https://visa.vfsglobal.com/aze/en/ita/dashboard"
BOOKING_URL    = "https://visa.vfsglobal.com/aze/en/ita/application-detail"

CHECK_INTERVAL = 180   # saniyə

NO_SLOT_TEXTS = [
    "no appointment slots",
    "no slots available",
    "no appointments available",
    "currently no appointment",
    "görüş vaxtları mövcud deyil",
    "no dates available",
    "sorry, there are no",
]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    print(f"[{now()}] {msg}", flush=True)


def send_whatsapp(message: str):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        log(f"✅ WhatsApp göndərildi: {msg.sid}")
    except Exception as e:
        log(f"❌ WhatsApp xətası: {e}")
        log(traceback.format_exc())


def do_login(page) -> bool:
    try:
        log(f"🔐 Login səhifəsi açılır: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("load", timeout=30000)
        time.sleep(2)
        log(f"📄 Səhifə: {page.title()} | URL: {page.url}")

        # Email
        log("🔍 Email sahəsi axtarılır...")
        email_selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[formcontrolname='username']",
            "input[formcontrolname='email']",
            "input[placeholder*='email' i]",
            "#email", "#username",
        ]
        email_field = None
        for sel in email_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    email_field = el
                    log(f"✅ Email sahəsi tapıldı: {sel}")
                    break
            except Exception:
                continue

        if not email_field:
            log("❌ Email sahəsi tapılmadı!")
            log(f"📄 Səhifə HTML (ilk 2000):\n{page.content()[:2000]}")
            return False

        email_field.fill(VFS_EMAIL)
        log(f"✅ Email yazıldı: {VFS_EMAIL}")
        time.sleep(0.5)

        # Şifrə
        log("🔍 Şifrə sahəsi axtarılır...")
        pass_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[formcontrolname='password']",
            "#password",
        ]
        pass_field = None
        for sel in pass_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    pass_field = el
                    log(f"✅ Şifrə sahəsi tapıldı: {sel}")
                    break
            except Exception:
                continue

        if not pass_field:
            log("❌ Şifrə sahəsi tapılmadı!")
            log(f"📄 Səhifə HTML (ilk 2000):\n{page.content()[:2000]}")
            return False

        pass_field.fill(VFS_PASSWORD)
        log("✅ Şifrə yazıldı")
        time.sleep(0.5)

        # Submit
        log("🔍 Login düyməsi axtarılır...")
        submit_selectors = [
            "button[type='submit']",
            "button:has-text('Sign In')",
            "button:has-text('Login')",
            "button:has-text('Log in')",
            "input[type='submit']",
        ]
        submit_btn = None
        for sel in submit_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    submit_btn = el
                    log(f"✅ Login düyməsi tapıldı: {sel}")
                    break
            except Exception:
                continue

        if not submit_btn:
            log("❌ Login düyməsi tapılmadı!")
            log(f"📄 Səhifə HTML (ilk 2000):\n{page.content()[:2000]}")
            return False

        submit_btn.click()
        log("✅ Login düyməsinə basıldı, gözlənilir...")
        time.sleep(3)
        page.wait_for_load_state("load", timeout=30000)

        log(f"📄 Login sonrası URL: {page.url}")
        log(f"📄 Login sonrası başlıq: {page.title()}")

        if "login" in page.url.lower():
            page_text = page.inner_text("body")
            log(f"❌ Login uğursuz — hələ login səhifəsindəyik")
            log(f"📄 Səhifə mətni (ilk 500):\n{page_text[:500]}")
            return False

        log("✅ Login uğurlu!")
        return True

    except PlaywrightTimeoutError as e:
        log(f"❌ Login timeout: {e}")
        log(traceback.format_exc())
        return False
    except Exception as e:
        log(f"❌ Login xətası: {e}")
        log(traceback.format_exc())
        return False


def select_dropdown(page, dropdown_index: int, preferred_texts: list) -> bool:
    try:
        selects = page.locator("mat-select").all()
        log(f"🔍 mat-select sayı: {len(selects)}")

        if len(selects) <= dropdown_index:
            log(f"❌ {dropdown_index}. dropdown yoxdur (cəmi {len(selects)})")
            return False

        selects[dropdown_index].click()
        time.sleep(1)
        page.wait_for_selector("mat-option", state="visible", timeout=8000)

        options = page.locator("mat-option").all()
        log(f"🔍 {len(options)} seçim var:")
        for opt in options:
            try:
                log(f"   • '{opt.inner_text().strip()}'")
            except Exception:
                pass

        for pref in preferred_texts:
            for opt in options:
                try:
                    if pref.lower() in opt.inner_text().lower():
                        txt = opt.inner_text().strip()
                        opt.click()
                        log(f"✅ Seçildi: '{txt}'")
                        time.sleep(1.5)
                        return True
                except Exception:
                    continue

        if options:
            txt = options[0].inner_text().strip()
            options[0].click()
            log(f"⚠️  Üstünlüklü seçim tapılmadı, ilki seçildi: '{txt}'")
            time.sleep(1.5)
            return True

        log(f"❌ {dropdown_index}. dropdown boşdur")
        return False

    except PlaywrightTimeoutError:
        log(f"❌ {dropdown_index}. dropdown timeout")
        return False
    except Exception as e:
        log(f"❌ {dropdown_index}. dropdown xətası: {e}")
        log(traceback.format_exc())
        return False


def check_slot() -> bool:
    log("=" * 60)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080",
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Baku",
        )
        # navigator.webdriver = false — bot aşkarlanmasının qarşısını al
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
        page = context.new_page()
        page.on("console",   lambda m: log(f"🖥️  [{m.type}] {m.text}"))
        page.on("pageerror", lambda e: log(f"🖥️  Brauzer xətası: {e}"))

        try:
            # 1. Login
            if not do_login(page):
                log("⛔ Login uğursuz — yoxlama atlanır")
                return False

            # 2. Application Detail (Start Booking)
            log(f"🌐 Booking səhifəsi açılır: {BOOKING_URL}")
            page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("load", timeout=30000)
            time.sleep(2)
            log(f"📄 URL: {page.url} | Başlıq: {page.title()}")

            # Login yönləndirildi?
            if "login" in page.url.lower():
                log("⚠️  Yenidən login tələb olunur...")
                if not do_login(page):
                    return False
                page.goto(BOOKING_URL, wait_until="networkidle", timeout=60000)
                time.sleep(2)

            # 3. "Start Booking" düyməsini tap və bas
            log("🔍 'Start Booking' düyməsi axtarılır...")
            start_btn = page.locator(
                "button:has-text('Start Booking'), "
                "a:has-text('Start Booking'), "
                "button:has-text('Book'), "
                "button:has-text('New Appointment')"
            )
            log(f"🔍 'Start Booking' sayı: {start_btn.count()}")
            if start_btn.count() > 0:
                start_btn.first.click()
                log("✅ 'Start Booking' düyməsinə basıldı")
                page.wait_for_load_state("load", timeout=30000)
                time.sleep(2)
                log(f"📄 Start Booking sonrası URL: {page.url}")
            else:
                log("⚠️  'Start Booking' tapılmadı — mövcud səhifə yoxlanır")
                log(f"📄 Səhifə mətni (ilk 800):\n{page.inner_text('body')[:800]}")

            # 4. Dropdown-ları seç
            log("🖱️  1. Mərkəz seçilir (Bakı)...")
            select_dropdown(page, 0, ["baku", "bakı", "italy", "italiya"])

            log("🖱️  2. Kateqoriya seçilir...")
            select_dropdown(page, 1, ["italy", "italiya", "viza", "visa"])

            log("🖱️  3. Alt kateqoriya seçilir (Turizm)...")
            select_dropdown(page, 2, ["turiz", "touris", "visit", "tourist"])

            time.sleep(3)

            # 5. Nəticəni yoxla
            page_text = page.inner_text("body")
            log(f"📄 Nəticə (ilk 600):\n{page_text[:600]}")

            for txt in NO_SLOT_TEXTS:
                if txt.lower() in page_text.lower():
                    log(f"❌ Slot yoxdur mətni tapıldı: '{txt}'")
                    return False

            # "Davam et" aktiv?
            btn = page.locator(
                "button:has-text('Next'), button:has-text('Continue'), button:has-text('Davam et')"
            )
            log(f"🔍 'Davam et' düyməsi sayı: {btn.count()}")
            if btn.count() > 0:
                enabled = btn.first.is_enabled()
                log(f"🔍 'Davam et' aktiv: {enabled}")
                if enabled:
                    return True

            log("⚠️  Nəticə aydın deyil — slot yoxdur kimi qəbul edilir")
            return False

        except PlaywrightTimeoutError as e:
            log(f"❌ Timeout xətası: {e}")
            log(traceback.format_exc())
            return False
        except Exception as e:
            log(f"❌ Gözlənilməz xəta: {e}")
            log(traceback.format_exc())
            return False
        finally:
            context.close()
            browser.close()
            log("🔒 Brauzer bağlandı")


def main():
    log("🚀 VFS İtaliya Slot İzləyici başladı!")
    log(f"📱 Bildiriş: {TO_WHATSAPP}")
    log(f"🔄 Yoxlama intervalı: hər {CHECK_INTERVAL} saniyə\n")

    send_whatsapp(
        "✅ VFS İtaliya Slot İzləyici işə düşdü!\n"
        "Boş görüş yeri açılanda dərhal xəbərdar edəcəyəm. 🇮🇹"
    )

    notified = False

    while True:
        log("🔍 Yoxlama başlayır...")
        slot_available = check_slot()

        if slot_available:
            if not notified:
                log("🎉 SLOT TAPILDI! WhatsApp göndərilir...")
                send_whatsapp(
                    "🎉 *SLOT AÇILDI!*\n\n"
                    "🇮🇹 İtaliya VFS Bakı - görüş yeri mövcuddur!\n\n"
                    "⚡ Dərhal keçin:\n"
                    "https://visa.vfsglobal.com/aze/en/ita/application-detail\n\n"
                    "⏰ Tez olun, tez dolar!"
                )
                notified = True
            else:
                log("ℹ️  Slot var, bildiriş artıq göndərilib")
        else:
            log(f"❌ Slot yoxdur. Növbəti yoxlama {CHECK_INTERVAL} saniyə sonra")
            notified = False

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
