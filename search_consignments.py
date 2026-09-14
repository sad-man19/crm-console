from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import json
import sys
from datetime import datetime

load_dotenv()

STEADFAST_EMAIL = os.getenv("STEADFAST_EMAIL")
STEADFAST_PASSWORD = os.getenv("STEADFAST_PASSWORD")
STEADFAST_STATE = "steadfast_state.json"

def save_state(context, filename):
    context.storage_state(path=filename)
    print(f"✅ State saved to {filename}")

def load_state(browser, filename):
    if os.path.exists(filename):
        context = browser.new_context(storage_state=filename)
        print(f"🍪 Using saved state from {filename}")
        return context
    return None

def login_steadfast(page, context):
    print("🔑 Logging into Steadfast...")
    page.goto("https://steadfast.com.bd/moderator/login")
    page.fill('input[name="email"]', STEADFAST_EMAIL)
    page.fill('input[name="password"]', STEADFAST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_selector('text=Dashboard', timeout=10000)
    save_state(context, STEADFAST_STATE)
    print("✅ Steadfast login successful!")

def extract_date(page):
    try:
        created_el = page.locator('p:has-text("Created at")').first
        if created_el.count() > 0:
            full_text = created_el.inner_text()
            parts = full_text.split("Created at :")
            if len(parts) > 1:
                return parts[1].strip()
            parts = full_text.split("Created at:")
            if len(parts) > 1:
                return parts[1].strip()
    except:
        pass
    return ""

def extract_link(page):
    try:
        copy_btn = page.locator('.copy-text').first
        if copy_btn.count() > 0 and copy_btn.is_visible():
            copy_btn.click()
            page.wait_for_timeout(500)
            link = page.evaluate("() => navigator.clipboard.readText()")
            if link:
                return link.strip()
    except:
        pass
    try:
        link_el = page.locator('span.bg-white').first
        if link_el.count() > 0:
            return link_el.inner_text().strip()
    except:
        pass
    return ""

def search_consignments(phone_number):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox', '--disable-images']
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                ignore_https_errors=True
            )
            context.grant_permissions(['clipboard-read', 'clipboard-write'])

            has_state = os.path.exists(STEADFAST_STATE)

            if has_state:
                ctx = load_state(browser, STEADFAST_STATE)
                if ctx:
                    context = ctx
                page = context.new_page()
                page.goto("https://steadfast.com.bd/dashboard", timeout=15000)
                page.wait_for_timeout(1000)
                if "moderator/login" in page.url:
                    print("⚠️ Session expired. Re-logging...")
                    context.close()
                    context = browser.new_context(viewport={'width': 1280, 'height': 720})
                    context.grant_permissions(['clipboard-read', 'clipboard-write'])
                    page = context.new_page()
                    page.goto("https://steadfast.com.bd/moderator/login")
                    login_steadfast(page, context)
                    page.goto("https://steadfast.com.bd/dashboard", timeout=15000)
                    page.wait_for_timeout(1000)
            else:
                context = browser.new_context(viewport={'width': 1280, 'height': 720})
                context.grant_permissions(['clipboard-read', 'clipboard-write'])
                page = context.new_page()
                page.goto("https://steadfast.com.bd/moderator/login")
                login_steadfast(page, context)

            # Block images, fonts, and media to speed up page loads
            page.route('**/*', lambda route: route.abort() if route.request.resource_type in ('image', 'font', 'media', 'stylesheet') else route.continue_())

            # Search
            search_selectors = [
                'input#searchInput',
                'input[placeholder*="Search Consignment"]',
                'input[placeholder*="Search"]',
                'input[type="text"]'
            ]
            search_input = None
            for sel in search_selectors:
                search_input = page.locator(sel).first
                if search_input.count() > 0:
                    break
            search_input.wait_for(state="visible", timeout=10000)
            search_input.fill(phone_number)
            search_btn = page.locator('button:has-text("Search"), button[type="submit"], button:has-text("Find"), .search-btn').first
            if search_btn.count() > 0 and search_btn.is_visible():
                search_btn.click()
            else:
                search_input.press('Enter')
            page.wait_for_timeout(1500)

            page_text = page.inner_text('body')
            if "Found Nothing" in page_text or "Nothing found" in page_text or "No results" in page_text:
                print("📭 Nothing found")
                browser.close()
                return {"result": "not_found", "message": "Steadfast Found Nothing!"}

            all_li = page.locator('#searchResults li').all()
            if len(all_li) == 0:
                print("⚠️ No results found")
                browser.close()
                return {"result": "not_found", "message": "Steadfast Found Nothing!"}

            print(f"📋 Found {len(all_li)} result(s)")

            results_list = []
            for i, li in enumerate(all_li):
                a = li.locator('a').first
                if a.count() == 0:
                    continue
                href = a.get_attribute('href') or ''
                if not href:
                    continue
                full_url = f'https://steadfast.com.bd{href}' if not href.startswith('http') else href

                new_page = context.new_page()
                try:
                    new_page.route('**/*', lambda route: route.abort() if route.request.resource_type in ('image', 'font', 'media', 'stylesheet') else route.continue_())
                    new_page.goto(full_url, timeout=15000, wait_until='domcontentloaded')
                    new_page.wait_for_timeout(1000)

                    link = extract_link(new_page)
                    date_text = extract_date(new_page)

                    if link or date_text:
                        results_list.append({"link": link, "date": date_text})
                        print(f"  [{i+1}] Link: {link} | Date: {date_text}")
                    else:
                        print(f"  [{i+1}] ⚠️ Empty result, skipping")

                    new_page.close()
                except Exception as e:
                    print(f"  [{i+1}] ❌ Error: {e}")
                    try:
                        new_page.close()
                    except:
                        pass

            def parse_date(d):
                try:
                    return datetime.strptime(d, "%B %d, %Y %I:%M %p")
                except:
                    try:
                        return datetime.strptime(d, "%B %d, %Y %H:%M %p")
                    except:
                        return datetime.min

            results_list.sort(key=lambda x: parse_date(x['date']), reverse=True)

            print(f"\n✅ Fetched {len(results_list)} results, sorted by date (latest first)")
            browser.close()
            return {
                "result": "found",
                "count": len(results_list),
                "results": results_list
            }

    except Exception as e:
        error_msg = f"Steadfast search error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"result": "error", "error": error_msg}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    else:
        phone = input("Enter phone number to search: ")

    result = search_consignments(phone)
    print(json.dumps(result, indent=2))
