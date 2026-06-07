import random
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]

async def create_browser_page(pw):
    """Launch Firefox with random viewport and user agent."""
    browser = await pw.firefox.launch(headless=True)
    context = await browser.new_context(
        viewport=random.choice(_VIEWPORTS),
        user_agent=random.choice(_USER_AGENTS),
        locale="en-US",
        timezone_id="Asia/Kolkata",
    )
    page = await context.new_page()
    # Warm-up
    try:
        await page.goto("https://www.naukri.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
    except Exception as e:
        logger.warning(f"Warm-up failed: {e}")
    return browser, page