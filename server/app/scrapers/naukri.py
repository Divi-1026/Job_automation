"""
Naukri.com job scraper — Playwright Firefox + stealth.

Uses Firefox instead of Chromium because Naukri's Akamai Bot Manager
blocks headless Chromium at the TLS fingerprint level.  Firefox's TLS
fingerprint is not blocked, and playwright-stealth hides the remaining
automation signals.

Selectors (same as the Selenium notebook):
  Card wrapper : .srp-jobtuple-wrapper
  Title        : .title
  Company      : .comp-name
  Location     : .loc-wrap
  Experience   : .exp-wrap
  Salary       : .sal-wrap
  Skills       : .tags-gt  →  li

URL pattern:
  https://www.naukri.com/{slug}-jobs-{page_num}
  (page_num starts at 0)

Public API
----------
scrape_one_skill(skill, max_jobs, page) → list[dict]
scrape_naukri(skills, max_per_skill)    → list[dict]
"""

import asyncio
import logging
import re
import random
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

_BASE = "https://www.naukri.com"
_STEALTH = Stealth()

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

_MIN_DELAY = 2.0
_MAX_DELAY = 4.0

# Firefox user-agents
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return text.strip() or None


# ── Card extraction (matches notebook selectors) ─────────────────────────────

async def _extract_card(card, skill: str) -> dict | None:
    """
    Extract job data from a single .srp-jobtuple-wrapper card.
    Uses the same class names as the Selenium notebook / YouTube video.
    """
    # Title — notebook uses By.CLASS_NAME "title"
    title_el = await card.query_selector(".title")
    if not title_el:
        return None

    title = _clean(await title_el.inner_text())
    if not title:
        return None

    # URL — get href if title element is an <a>, or find <a> inside it
    url = await title_el.get_attribute("href")
    if not url:
        a_el = await card.query_selector("a.title")
        if a_el:
            url = await a_el.get_attribute("href")

    # Company — notebook uses By.CLASS_NAME "comp-name"
    company_el = await card.query_selector(".comp-name")
    company = _clean(await company_el.inner_text()) if company_el else None

    # Location — notebook uses By.CLASS_NAME "loc-wrap"
    loc_el = await card.query_selector(".loc-wrap")
    location = _clean(await loc_el.inner_text()) if loc_el else None

    # Experience — notebook uses By.CLASS_NAME "exp-wrap"
    exp_el = await card.query_selector(".exp-wrap")
    exp = _clean(await exp_el.inner_text()) if exp_el else None
    if exp:
        exp = exp.replace(" Yrs", "").replace(" yrs", "").strip() or None

    # Salary — notebook uses By.CLASS_NAME "sal-wrap"
    sal_el = await card.query_selector(".sal-wrap")
    salary = _clean(await sal_el.inner_text()) if sal_el else None
    if salary:
        salary = (
            salary.replace(" Lacs PA", "")
                  .replace(" lacs pa", "")
                  .replace("Not disclosed", "")
                  .strip() or None
        )

    # Skills — notebook uses By.CLASS_NAME "tags-gt" → find_elements(By.TAG_NAME, "li")
    skill_lis = await card.query_selector_all(".tags-gt li")
    skills_list = []
    for li in skill_lis:
        s = _clean(await li.inner_text())
        if s:
            skills_list.append(s)
    skills_str = ", ".join(skills_list) if skills_list else None

    desc_parts = []
    if exp:
        desc_parts.append(f"Exp: {exp}")
    if skills_str:
        desc_parts.append(f"Skills: {skills_str}")

    return {
        "title":       title,
        "company":     company,
        "location":    location,
        "salary":      salary,
        "url":         url,
        "source":      "naukri",
        "skill_query": skill,
        "description": " | ".join(desc_parts) if desc_parts else None,
    }


# ── Single-skill scrape (uses caller's page) ──────────────────────────────────

async def scrape_one_skill(
    skill: str,
    max_jobs: int,
    page,           # existing Playwright Page — caller owns lifecycle
) -> list[dict]:
    """
    Scrape `max_jobs` jobs for one skill on the given Playwright page.
    URL pattern matches the notebook: {skill}-jobs-{i}  (i starts at 0).
    """
    slug = _slugify(skill)
    jobs: list[dict] = []
    seen: set[str] = set()
    pages_needed = max(1, (max_jobs + 19) // 20)   # ~20 results per Naukri page

    for page_num in range(pages_needed):
        if len(jobs) >= max_jobs:
            break

        # URL pattern from notebook: "https://www.naukri.com/{}-jobs-{}".format(skill, i)
        url = f"{_BASE}/{slug}-jobs-{page_num}"
        logger.info(f"[Naukri] Fetching: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            # Wait for page to settle (notebook uses time.sleep(3))
            await asyncio.sleep(3)

            try:
                await page.wait_for_selector(".srp-jobtuple-wrapper", timeout=15_000)
            except PWTimeout:
                logger.warning(f"[Naukri] No job cards found at {url} (CAPTCHA or empty page)")
                break

            # notebook: driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
            cards = await page.query_selector_all(".srp-jobtuple-wrapper")
            logger.info(f"[Naukri] Found {len(cards)} card(s) on page {page_num}")
            if not cards:
                break

            for card in cards:
                if len(jobs) >= max_jobs:
                    break
                try:
                    job = await _extract_card(card, skill)
                    if not job:
                        continue
                    key = job.get("url") or f"{job['title']}|{job['company']}"
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Naukri] Card extraction error: {e}")
                    continue

        except PWTimeout:
            logger.warning(f"[Naukri] Timeout loading {url}")
            continue
        except Exception as e:
            logger.warning(f"[Naukri] Error loading {url}: {e}")
            continue

        await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))

    logger.info(f"[Naukri] Scraped {len(jobs)} job(s) for skill '{skill}'")
    return jobs


# ── Browser factory helper (shared by loop and standalone use) ────────────────

async def _make_browser_page(pw):
    """Launch Firefox with stealth settings, return (browser, page)."""
    browser = await pw.firefox.launch(headless=True)
    context = await browser.new_context(
        viewport=random.choice(_VIEWPORTS),
        user_agent=random.choice(_USER_AGENTS),
        locale="en-US",
        timezone_id="Asia/Kolkata",
    )
    await _STEALTH.apply_stealth_async(context)

    page = await context.new_page()

    # Warm-up: get session cookies (same as opening Naukri in browser first)
    logger.info("[Naukri] Warming up browser — fetching naukri.com homepage")
    try:
        await page.goto(_BASE, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
    except Exception as e:
        logger.warning(f"[Naukri] Warm-up failed: {e}")
    return browser, page


# ── Standalone convenience wrapper ────────────────────────────────────────────

async def scrape_naukri(skills: list[str], max_per_skill: int = 10) -> list[dict]:
    """Scrape all skills, owning the browser lifecycle internally."""
    all_jobs: list[dict] = []
    async with async_playwright() as pw:
        browser, page = await _make_browser_page(pw)
        for skill in skills:
            try:
                jobs = await scrape_one_skill(skill, max_per_skill, page)
                all_jobs.extend(jobs)
            except Exception:
                continue
            await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))
        await browser.close()
    return all_jobs