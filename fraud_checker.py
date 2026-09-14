from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor
import time
import os
import json
import re
import sys

# ============================================================
#  CONFIGURATION
# ============================================================
load_dotenv()

STEADFAST_EMAIL = os.getenv("STEADFAST_EMAIL")
STEADFAST_PASSWORD = os.getenv("STEADFAST_PASSWORD")
PATHAO_EMAIL = os.getenv("PATHAO_EMAIL")
PATHAO_PASSWORD = os.getenv("PATHAO_PASSWORD")

STEADFAST_STATE = "steadfast_state.json"
PATHAO_STATE = "pathao_state.json"

# ============================================================

def save_state(context, filename):
    context.storage_state(path=filename)
    print(f"✅ State saved to {filename}")

def load_state(browser, filename):
    if os.path.exists(filename):
        context = browser.new_context(storage_state=filename)
        print(f"🍪 Using saved state from {filename}")
        return context
    return None

# ------------------------------------------------------------------
#  LOGIN FUNCTIONS (with reduced wait times)
# ------------------------------------------------------------------
def login_steadfast(page, context):
    print("🔑 Logging into Steadfast...")
    page.goto("https://steadfast.com.bd/moderator/login")
    page.fill('input[name="email"]', STEADFAST_EMAIL)
    page.fill('input[name="password"]', STEADFAST_PASSWORD)
    page.click('button[type="submit"]')
    # Replace fixed wait with smart wait
    page.wait_for_selector('text=Dashboard', timeout=10000)
    save_state(context, STEADFAST_STATE)
    print("✅ Steadfast login successful!")

def login_pathao(page, context):
    """Log into Pathao and save state."""
    print("🔑 Logging into Pathao...")
    page.goto("https://merchant.pathao.com/login")
    
    # Wait for login form to load
    page.wait_for_selector('input[name="email"]', state="visible", timeout=10000)
    page.fill('input[name="email"]', PATHAO_EMAIL)
    page.fill('input[name="password"]', PATHAO_PASSWORD)
    page.click('button:has-text("Sign In")')
    
    # Wait for successful login - look for dashboard elements
    try:
        # Option 1: Wait for the dashboard or order creation link
        page.wait_for_selector('text=Create Order', timeout=8000)
    except:
        # Option 2: Wait for the URL to change to dashboard
        page.wait_for_url("**/courier/**", timeout=10000)
    
    save_state(context, PATHAO_STATE)
    print("✅ Pathao login successful!")

# ------------------------------------------------------------------
#  CHECK FUNCTIONS (optimized)
# ------------------------------------------------------------------
def check_steadfast(phone_number):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = load_state(browser, STEADFAST_STATE)

            if context is None:
                context = browser.new_context()
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                login_steadfast(page, context)
                page.goto("https://steadfast.com.bd/user/frauds/check")
            else:
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                page.goto("https://steadfast.com.bd/user/frauds/check", timeout=10000)
                if "Logout" not in page.inner_text('body'):
                    print("⚠️ Steadfast session expired. Re‑logging...")
                    context.close()
                    context = browser.new_context()
                    page = context.new_page()
                    page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                    login_steadfast(page, context)
                    page.goto("https://steadfast.com.bd/user/frauds/check")
                else:
                    print("✅ Steadfast session valid")

            print(f"📞 Checking Steadfast for: {phone_number}")
            page.fill('input[placeholder="Search by phone number"]', phone_number)
            page.click('button:has-text("Search")')
            page.wait_for_selector('text=Success', timeout=8000)

            page_text = page.inner_text('body')
            success_match = re.search(r'Success\s*:\s*(\d+)', page_text)
            cancel_match = re.search(r'Cancellation\s*:\s*(\d+)', page_text)

            success = success_match.group(1) if success_match else "N/A"
            cancellation = cancel_match.group(1) if cancel_match else "N/A"

            browser.close()
            return {"success": success, "cancellation": cancellation, "error": None}
    except Exception as e:
        error_msg = f"Steadfast error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": "N/A", "cancellation": "N/A", "error": error_msg}

def check_pathao(phone_number):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = load_state(browser, PATHAO_STATE)

            if context is None:
                context = browser.new_context()
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                login_pathao(page, context)
                page.goto("https://merchant.pathao.com/courier/orders/create")
                page.wait_for_selector('input[name="recipient_phone"]', state="visible", timeout=10000)
            else:
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                try:
                    page.goto("https://merchant.pathao.com/courier/orders/create", timeout=15000)
                    page.wait_for_selector('input[name="recipient_phone"]', state="visible", timeout=8000)
                    print("✅ Pathao session valid")
                except Exception as e:
                    print(f"⚠️ Pathao session invalid or timed out: {str(e)[:100]}")
                    print("🔄 Re‑logging...")
                    context.close()
                    context = browser.new_context()
                    page = context.new_page()
                    page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
                    login_pathao(page, context)
                    page.goto("https://merchant.pathao.com/courier/orders/create")
                    page.wait_for_selector('input[name="recipient_phone"]', state="visible", timeout=10000)

            print(f"📞 Checking Pathao for: {phone_number}")
            page.fill('input[name="recipient_phone"]', phone_number)
            
            try:
                page.wait_for_selector('text=Processed', timeout=5000)
            except:
                pass

            page_text = page.inner_text('body')
            processed_match = re.search(r'Processed\s*[:]?\s*(\d+)', page_text)
            delivered_match = re.search(r'Delivered\s*[:]?\s*(\d+)', page_text)
            returned_match = re.search(r'Returned\s*[:]?\s*(\d+)', page_text)

            processed = processed_match.group(1) if processed_match else "N/A"
            delivered = delivered_match.group(1) if delivered_match else "N/A"
            returned = returned_match.group(1) if returned_match else "N/A"
            print(f"   Processed: {processed}, Delivered: {delivered}, Returned: {returned}")

            # --- HANDLE ADDRESS POPUP ---
            try:
                popup_cancel = page.locator('button:has-text("Cancel")').first
                if popup_cancel.count() > 0 and popup_cancel.is_visible():
                    print("🔄 Existing customer – closing address popup...")
                    popup_cancel.click()
                    page.wait_for_timeout(500)
                    print("✅ Popup cancelled")
            except Exception as e:
                print("ℹ️ No address popup (new customer)")

            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            if current_url == "about:blank" or "orders/create" not in current_url:
                print("ℹ️ Order creation already cancelled")
                browser.close()
                return {
                    "processed": processed,
                    "delivered": delivered,
                    "returned": returned,
                    "error": None
                }

            print("🔄 Cancelling order creation...")
            cancel_success = False
            
            if page.locator('input[name="recipient_phone"]').count() == 0:
                print("ℹ️ Order form already gone")
                browser.close()
                return {
                    "processed": processed,
                    "delivered": delivered,
                    "returned": returned,
                    "error": None
                }
            
            cancel_selectors = [
                'button:has-text("Cancel")',
                '.pt-btn-outline.pt-btn-danger-outline',
                'button[class*="cancel"]',
                'button.pt-btn.pt-btn-outline'
            ]
            
            for selector in cancel_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.click(selector)
                        print(f"✅ Order creation cancelled")
                        cancel_success = True
                        break
                except:
                    continue
            
            if not cancel_success:
                try:
                    page.fill('input[name="recipient_phone"]', '')
                    print("✅ Order creation cancelled (cleared phone field)")
                    cancel_success = True
                except:
                    pass
            
            if not cancel_success:
                print("ℹ️ Order creation already cancelled or not needed")

            browser.close()
            return {
                "processed": processed,
                "delivered": delivered,
                "returned": returned,
                "error": None
            }
    except Exception as e:
        error_msg = f"Pathao error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "processed": "N/A",
            "delivered": "N/A",
            "returned": "N/A",
            "error": error_msg
        }

# ------------------------------------------------------------------
#  COMBINED CHECK
# ------------------------------------------------------------------
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def check_both(phone_number):
    print("\n" + "=" * 60)
    print(f"📊 CHECKING BOTH COURIERS FOR: {phone_number}")
    print("=" * 60 + "\n")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        future_steadfast = executor.submit(check_steadfast, phone_number)
        future_pathao = executor.submit(check_pathao, phone_number)
        
        steadfast_result = future_steadfast.result()
        pathao_result = future_pathao.result()
    
    elapsed = time.time() - start_time
    
    # Check for errors
    steadfast_error = steadfast_result.get("error")
    pathao_error = pathao_result.get("error")
    
    if steadfast_error:
        print(f"⚠️ Steadfast had an error: {steadfast_error}")
    if pathao_error:
        print(f"⚠️ Pathao had an error: {pathao_error}")
    
    print(f"\n⏱️ Total time: {elapsed:.2f} seconds")
    
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS for {phone_number}:")
    print("=" * 60)

    print("\n📦 Pathao Courier:")
    if pathao_error:
        print(f"   ❌ Error: {pathao_error}")
    else:
        print(f"   ✅ Processed: {pathao_result['processed']}")
        print(f"   ✅ Delivered: {pathao_result['delivered']}")
        print(f"   ❌ Returned: {pathao_result['returned']}")

    print("\n📦 Steadfast Courier:")
    if steadfast_error:
        print(f"   ❌ Error: {steadfast_error}")
    else:
        print(f"   ✅ Success: {steadfast_result['success']}")
        print(f"   ❌ Cancellation: {steadfast_result['cancellation']}")

    print("\n" + "=" * 60)
    
    return {
        "pathao": pathao_result,
        "steadfast": steadfast_result,
        "elapsed": elapsed
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    else:
        phone = input("Enter phone number to check: ")

    result = check_both(phone)