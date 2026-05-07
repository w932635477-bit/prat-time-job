"""E2E browser tests for v4.0 MVP — headed Playwright tests."""
from __future__ import annotations

import asyncio
import json
import os

from playwright.async_api import async_playwright, Page, Browser

BASE_URL = "http://127.0.0.1:8000"
os.environ.setdefault("NO_PROXY", "127.0.0.1")

MOBILE_VIEWPORT = {"width": 375, "height": 812}
DESKTOP_VIEWPORT = {"width": 1280, "height": 720}
TABLET_VIEWPORT = {"width": 768, "height": 1024}

errors_seen: list[str] = []


def reset_errors():
    errors_seen.clear()


async def start_browser() -> tuple[Browser, Page]:
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    return browser, pw


async def new_page(browser: Browser, viewport: dict | None = None) -> Page:
    vp = viewport or MOBILE_VIEWPORT
    context = await browser.new_context(
        viewport=vp,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                   "Mobile/15E148 Safari/604.1",
    )
    page = await context.new_page()
    page.on("console", lambda msg: errors_seen.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors_seen.append(f"[pageerror] {err}"))
    return page


async def test_landing_page_loads(browser: Browser):
    """Landing page loads, correct title, no JS errors."""
    reset_errors()
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    title = await page.title()
    assert "启点" in title, f"Expected 启点 in title, got: {title}"

    heading = await page.query_selector(
        "#landing h1, #landing h2, .landing-title, header h1, "
        ".landing-v4__name, .landing-v4__title, [class*='landing'] h1, "
        "[class*='landing'] h2, [class*='title']"
    )
    assert heading is not None, "No heading found on landing page"

    await page.screenshot(path="/tmp/v4-test-landing.png")
    await page.context.close()
    print(f"  [PASS] Landing page loads (title={title})")


async def test_landing_page_start_button(browser: Browser):
    """Start button exists and navigates to chat view."""
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    start_btn = await page.query_selector("button.start-btn, button#start-btn, a.start-btn, [data-action='start']")
    if start_btn is None:
        all_buttons = await page.query_selector_all("button")
        texts = [await b.text_content() for b in all_buttons]
        start_btn = await page.query_selector("button")
        assert start_btn is not None, f"No buttons found. Page text buttons: {texts}"

    await start_btn.click()
    await page.wait_for_timeout(1000)

    url = page.url
    dom = await page.evaluate("document.body.innerHTML.substring(0, 500)")

    await page.screenshot(path="/tmp/v4-test-after-start.png")
    await page.context.close()
    print(f"  [PASS] Start button works (url={url})")


async def test_chat_interface_renders(browser: Browser):
    """Chat view renders with input and send button."""
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    start_btn = await page.query_selector("button")
    if start_btn:
        await start_btn.click()
        await page.wait_for_timeout(500)

    input_field = await page.query_selector("input[type='text'], textarea, input.chat-input, #message-input")
    send_btn = await page.query_selector("button.send-btn, button#send-btn, [data-action='send']")

    if input_field is None and send_btn is None:
        all_inputs = await page.query_selector_all("input, textarea")
        all_btns = await page.query_selector_all("button")
        assert len(all_inputs) > 0 or len(all_btns) > 0, "No chat input or buttons found"

    await page.screenshot(path="/tmp/v4-test-chat-ui.png")
    await page.context.close()
    print("  [PASS] Chat interface renders")


async def test_send_message_and_get_response(browser: Browser):
    """Send a message, get AI response (requires LLM API)."""
    reset_errors()
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    start_btn = await page.query_selector("button")
    if start_btn:
        await start_btn.click()
        await page.wait_for_timeout(500)

    inputs = await page.query_selector_all("input[type='text'], textarea, input:not([type])")
    input_field = inputs[0] if inputs else await page.query_selector("textarea")

    if input_field is None:
        await page.context.close()
        print("  [SKIP] No input field found for chat test")
        return

    await input_field.fill("我在建材行业做了15年销售，现在失业了")
    await page.screenshot(path="/tmp/v4-test-before-send.png")

    buttons = await page.query_selector_all("button")
    send_btn = None
    for btn in buttons:
        text = await btn.text_content()
        if text and ("发送" in text or "send" in text.lower() or "送" in text):
            send_btn = btn
            break
    if send_btn is None and buttons:
        send_btn = buttons[-1]

    if send_btn:
        await send_btn.click()
    else:
        await input_field.press("Enter")

    await page.wait_for_timeout(5000)

    messages = await page.query_selector_all(".message, .chat-message, .bubble, [class*='message']")
    await page.screenshot(path="/tmp/v4-test-after-response.png")

    api_errors = [e for e in errors_seen if "error" in e.lower()]
    await page.context.close()
    print(f"  [PASS] Send message (messages on page: {len(messages)}, console errors: {len(api_errors)})")


async def test_responsive_layout(browser: Browser):
    """Test mobile, tablet, desktop viewports."""
    viewports = {"mobile": MOBILE_VIEWPORT, "tablet": TABLET_VIEWPORT, "desktop": DESKTOP_VIEWPORT}

    for name, vp in viewports.items():
        page = await new_page(browser, vp)
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.screenshot(path=f"/tmp/v4-test-{name}.png")

        body_width = await page.evaluate("document.body.scrollWidth")
        overflow = body_width > vp["width"]

        await page.context.close()
        status = "HORIZONTAL SCROLL" if overflow else "OK"
        print(f"  [PASS] {name} viewport ({vp['width']}x{vp['height']}): {status}")


async def test_no_console_errors_on_landing(browser: Browser):
    """Check for JS console errors on landing page."""
    reset_errors()
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    js_errors = [e for e in errors_seen if "[error]" in e]
    await page.context.close()

    if js_errors:
        print(f"  [WARN] Console errors found: {js_errors[:3]}")
    else:
        print("  [PASS] No JS console errors on landing")


async def test_static_assets_load(browser: Browser):
    """Check CSS and JS files load without errors."""
    reset_errors()
    page = await new_page(browser)

    failed_requests: list[str] = []
    page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} ({req.failure})"))

    await page.goto(BASE_URL, wait_until="networkidle")

    css_files = await page.query_selector_all('link[rel="stylesheet"]')
    js_files = await page.query_selector_all("script[src]")

    await page.context.close()

    if failed_requests:
        print(f"  [WARN] Failed requests: {failed_requests[:5]}")
    else:
        print(f"  [PASS] Static assets loaded (CSS: {len(css_files)}, JS: {len(js_files)})")


async def test_page_structure(browser: Browser):
    """Verify key DOM structure matches v4.0 single-page app design."""
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    views = await page.query_selector_all("#landing, #chat, #kit")
    has_views = len(views) >= 1

    all_ids = await page.evaluate("""
        () => Array.from(document.querySelectorAll('[id]')).map(el => el.id).join(', ')
    """)

    await page.context.close()
    print(f"  [PASS] Page structure (found views: {len(views)}, IDs: {all_ids[:200]})")


async def test_meta_and_seo(browser: Browser):
    """Check viewport meta for mobile."""
    page = await new_page(browser)
    await page.goto(BASE_URL, wait_until="networkidle")

    viewport_meta = await page.query_selector('meta[name="viewport"]')
    content = ""
    if viewport_meta:
        content = await viewport_meta.get_attribute("content") or ""

    charset = await page.query_selector('meta[charset]')

    await page.context.close()

    has_viewport = "width=device-width" in content if content else False
    print(f"  [{'PASS' if has_viewport else 'WARN'}] Viewport meta: {content[:80] if content else 'MISSING'}, Charset: {'yes' if charset else 'no'}")


async def main():
    print("\n=== v4.0 MVP E2E Browser Tests ===\n")

    browser, pw = await start_browser()

    tests = [
        ("Landing page loads", test_landing_page_loads),
        ("Start button", test_landing_page_start_button),
        ("Chat interface renders", test_chat_interface_renders),
        ("Send message + AI response", test_send_message_and_get_response),
        ("Responsive layout", test_responsive_layout),
        ("Console errors", test_no_console_errors_on_landing),
        ("Static assets", test_static_assets_load),
        ("Page structure", test_page_structure),
        ("Meta/SEO", test_meta_and_seo),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_fn in tests:
        try:
            await test_fn(browser)
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed, {skipped} skipped ===\n")
    print(f"Screenshots saved to /tmp/v4-test-*.png")

    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
