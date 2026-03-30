"""
Indeed job scraper — Playwright Firefox + stealth.

Uses the same Firefox browser as the Naukri scraper (shared page).
Indeed blocks httpx/requests (403), so we use Playwright to render
the page and extract job cards from the DOM.

Selectors (discovered from indeed.com rendered HTML):
  Card wrapper : .tapItem
  Title        : h2 a span[title]
  Company      : [data-testid="company-name"]
  Location     : [data-testid="text-location"]
  Job link     : h2 a[data-jk]  →  data-jk attr used to build viewjob URL

URL pattern:
  https://www.indeed.com/jobs?q={skill}&l=India&start={page*10}

Public API
----------
scrape_one_skill_indeed(skill, max_jobs, page) → list[dict]
scrape_indeed(skills, max_per_skill)           → list[dict]   (standalone)
"""

import asyncio
import logging
import re
import random
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

_BASE = "https://www.indeed.com"
_SEARCH = f"{_BASE}/jobs"

_MIN_DELAY = 2.0
_MAX_DELAY = 4.0


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return text.strip() or None


async def _extract_card(card, skill: str) -> dict | None:
    """Extract job data from a single .tapItem card."""
    title_el = await card.query_selector("h2 a span[title]")
    if not title_el:
        return None

    title = _clean(await title_el.get_attribute("title"))
    if not title:
        return None

    # Job key for URL
    link_el = await card.query_selector("h2 a[data-jk]")
    jk = await link_el.get_attribute("data-jk") if link_el else None
    url = f"{_BASE}/viewjob?jk={jk}" if jk else None

    company_el = await card.query_selector("[data-testid='company-name']")
    company = _clean(await company_el.inner_text()) if company_el else None

    loc_el = await card.query_selector("[data-testid='text-location']")
    location = _clean(await loc_el.inner_text()) if loc_el else None

    # Salary (sometimes present)
    salary_el = await card.query_selector("[data-testid='attribute_snippet_testid']")
    salary = _clean(await salary_el.inner_text()) if salary_el else None

    # Snippet / description
    snippet_el = await card.query_selector("[data-testid='belowJobSnippet'] li")
    snippet = _clean(await snippet_el.inner_text()) if snippet_el else None

    return {
        "title":       title,
        "company":     company,
        "location":    location,
        "salary":      salary,
        "url":         url,
        "source":      "indeed",
        "skill_query": skill,
        "description": snippet,
    }


async def scrape_one_skill_indeed(
    skill: str,
    max_jobs: int,
    page,           # existing Playwright Page — caller owns lifecycle
) -> list[dict]:
    """Scrape `max_jobs` Indeed jobs for one skill on the given Playwright page."""
    jobs: list[dict] = []
    seen: set[str] = set()
    pages_needed = max(1, (max_jobs + 14) // 15)   # ~15 results per Indeed page

    for page_num in range(pages_needed):
        if len(jobs) >= max_jobs:
            break

        url = f"{_SEARCH}?q={skill}&l=India&start={page_num * 10}"
        logger.info(f"[Indeed] Fetching: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            await asyncio.sleep(3)

            try:
                await page.wait_for_selector(".tapItem", timeout=15_000)
            except PWTimeout:
                logger.warning(f"[Indeed] No job cards found at {url}")
                break

            cards = await page.query_selector_all(".tapItem")
            logger.info(f"[Indeed] Found {len(cards)} card(s) on page {page_num}")
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
                    logger.debug(f"[Indeed] Card extraction error: {e}")
                    continue

        except PWTimeout:
            logger.warning(f"[Indeed] Timeout loading {url}")
            continue
        except Exception as e:
            logger.warning(f"[Indeed] Error loading {url}: {e}")
            continue

        await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))

    logger.info(f"[Indeed] Scraped {len(jobs)} job(s) for skill '{skill}'")
    return jobs


async def scrape_indeed(skills: list[str], max_per_skill: int = 10) -> list[dict]:
    """Standalone wrapper — launches its own Firefox browser."""
    from app.scrapers.naukri import _make_browser_page

    all_jobs: list[dict] = []
    async with async_playwright() as pw:
        browser, page = await _make_browser_page(pw)
        for skill in skills:
            try:
                jobs = await scrape_one_skill_indeed(skill, max_per_skill, page)
                all_jobs.extend(jobs)
            except Exception:
                continue
            await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))
        await browser.close()
    return all_jobs
