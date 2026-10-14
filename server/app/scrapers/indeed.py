# """
# Indeed job scraper — Playwright Firefox + stealth.

# Uses the same Firefox browser as the Naukri scraper (shared page).
# Indeed blocks httpx/requests (403), so we use Playwright to render
# the page and extract job cards from the DOM.

# Selectors (discovered from indeed.com rendered HTML):
#   Card wrapper : .tapItem
#   Title        : h2 a span[title]
#   Company      : [data-testid="company-name"]
#   Location     : [data-testid="text-location"]
#   Job link     : h2 a[data-jk]  →  data-jk attr used to build viewjob URL

# URL pattern:
#   https://www.indeed.com/jobs?q={skill}&l=India&start={page*10}

# Public API
# ----------
# scrape_one_skill_indeed(skill, max_jobs, page) → list[dict]
# scrape_indeed(skills, max_per_skill)           → list[dict]   (standalone)
# """

# import asyncio
# import logging
# import re
# import random
# from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# logger = logging.getLogger(__name__)

# _BASE = "https://www.indeed.com"
# _SEARCH = f"{_BASE}/jobs"

# _MIN_DELAY = 2.0
# _MAX_DELAY = 4.0


# def _clean(text: str | None) -> str | None:
#     if not text:
#         return None
#     return text.strip() or None


# async def _extract_card(card, skill: str) -> dict | None:
#     """Extract job data from a single .tapItem card."""
#     title_el = await card.query_selector("h2 a span[title]")
#     if not title_el:
#         return None

#     title = _clean(await title_el.get_attribute("title"))
#     if not title:
#         return None

#     # Job key for URL
#     link_el = await card.query_selector("h2 a[data-jk]")
#     jk = await link_el.get_attribute("data-jk") if link_el else None
#     url = f"{_BASE}/viewjob?jk={jk}" if jk else None

#     company_el = await card.query_selector("[data-testid='company-name']")
#     company = _clean(await company_el.inner_text()) if company_el else None

#     loc_el = await card.query_selector("[data-testid='text-location']")
#     location = _clean(await loc_el.inner_text()) if loc_el else None

#     # Salary (sometimes present)
#     salary_el = await card.query_selector("[data-testid='attribute_snippet_testid']")
#     salary = _clean(await salary_el.inner_text()) if salary_el else None

#     # Snippet / description
#     snippet_el = await card.query_selector("[data-testid='belowJobSnippet'] li")
#     snippet = _clean(await snippet_el.inner_text()) if snippet_el else None

#     return {
#         "title":       title,
#         "company":     company,
#         "location":    location,
#         "salary":      salary,
#         "url":         url,
#         "source":      "indeed",
#         "skill_query": skill,
#         "description": snippet,
#     }


# async def scrape_one_skill_indeed(
#     skill: str,
#     max_jobs: int,
#     page,           # existing Playwright Page — caller owns lifecycle
# ) -> list[dict]:
#     """Scrape `max_jobs` Indeed jobs for one skill on the given Playwright page."""
#     jobs: list[dict] = []
#     seen: set[str] = set()
#     pages_needed = max(1, (max_jobs + 14) // 15)   # ~15 results per Indeed page

#     for page_num in range(pages_needed):
#         if len(jobs) >= max_jobs:
#             break

#         url = f"{_SEARCH}?q={skill}&l=India&start={page_num * 10}"
#         logger.info(f"[Indeed] Fetching: {url}")
#         try:
#             await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
#             await asyncio.sleep(3)

#             try:
#                 await page.wait_for_selector(".tapItem", timeout=15_000)
#             except PWTimeout:
#                 logger.warning(f"[Indeed] No job cards found at {url}")
#                 break

#             cards = await page.query_selector_all(".tapItem")
#             logger.info(f"[Indeed] Found {len(cards)} card(s) on page {page_num}")
#             if not cards:
#                 break

#             for card in cards:
#                 if len(jobs) >= max_jobs:
#                     break
#                 try:
#                     job = await _extract_card(card, skill)
#                     if not job:
#                         continue
#                     key = job.get("url") or f"{job['title']}|{job['company']}"
#                     if key in seen:
#                         continue
#                     seen.add(key)
#                     jobs.append(job)
#                 except Exception as e:
#                     logger.debug(f"[Indeed] Card extraction error: {e}")
#                     continue

#         except PWTimeout:
#             logger.warning(f"[Indeed] Timeout loading {url}")
#             continue
#         except Exception as e:
#             logger.warning(f"[Indeed] Error loading {url}: {e}")
#             continue

#         await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))

#     logger.info(f"[Indeed] Scraped {len(jobs)} job(s) for skill '{skill}'")
#     return jobs


# async def scrape_indeed(skills: list[str], max_per_skill: int = 10) -> list[dict]:
#     """Standalone wrapper — launches its own Firefox browser."""
#     from app.scrapers.naukri import _make_browser_page

#     all_jobs: list[dict] = []
#     async with async_playwright() as pw:
#         browser, page = await _make_browser_page(pw)
#         for skill in skills:
#             try:
#                 jobs = await scrape_one_skill_indeed(skill, max_per_skill, page)
#                 all_jobs.extend(jobs)
#             except Exception:
#                 continue
#             await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))
#         await browser.close()
#     return all_jobs
"""
Indeed job scraper — Playwright Firefox.

Uses an existing Playwright page when called from the global scraper.

The scraper intentionally uses multiple selector fallbacks because Indeed
changes its DOM structure frequently.

Public API
----------
scrape_one_skill_indeed(skill, max_jobs, page) -> list[dict]
scrape_indeed(skills, max_per_skill)           -> list[dict]
"""

import asyncio
import logging
import random
from urllib.parse import quote_plus, urljoin

from playwright.async_api import (
    async_playwright,
    TimeoutError as PWTimeout,
)

logger = logging.getLogger(__name__)


BASE_URL = "https://www.indeed.com"
SEARCH_URL = f"{BASE_URL}/jobs"

MIN_DELAY = 2.0
MAX_DELAY = 4.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(text: str | None) -> str | None:
    if not text:
        return None

    text = " ".join(text.split()).strip()
    return text or None


async def _first_element(parent, selectors: list[str]):
    """
    Return first element found from selector list.
    """
    for selector in selectors:
        try:
            element = await parent.query_selector(selector)
            if element:
                return element
        except Exception:
            continue

    return None


async def _safe_text(parent, selectors: list[str]) -> str | None:
    """
    Get inner text using selector fallbacks.
    """
    element = await _first_element(parent, selectors)

    if not element:
        return None

    try:
        return _clean(await element.inner_text())
    except Exception:
        return None


async def _safe_attr(
    parent,
    selectors: list[str],
    attribute: str,
) -> str | None:
    """
    Get an attribute using selector fallbacks.
    """
    element = await _first_element(parent, selectors)

    if not element:
        return None

    try:
        return _clean(await element.get_attribute(attribute))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Block / CAPTCHA detection
# ---------------------------------------------------------------------------

async def _page_is_blocked(page) -> bool:
    """
    Detect common Indeed anti-bot / challenge pages.
    """

    try:
        title = (await page.title()).lower()
    except Exception:
        title = ""

    try:
        body = (await page.locator("body").inner_text()).lower()
    except Exception:
        body = ""

    markers = [
        "captcha",
        "additional verification required",
        "verify you are human",
        "security check",
        "unusual traffic",
        "access denied",
        "are you a robot",
    ]

    combined = f"{title} {body}"

    return any(marker in combined for marker in markers)


# ---------------------------------------------------------------------------
# Extract one job
# ---------------------------------------------------------------------------

async def _extract_card(card, skill: str) -> dict | None:
    """
    Extract one Indeed job card using multiple selector fallbacks.
    """

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    title_element = await _first_element(
        card,
        [
            "a.jcs-JobTitle",
            "h2.jobTitle a",
            "h2 a[data-jk]",
            "h2 a",
            "a[data-jk]",
            "[data-testid='job-title'] a",
        ],
    )

    if not title_element:
        return None

    title = None

    # Try title attribute first
    try:
        title = _clean(
            await title_element.get_attribute("aria-label")
        )
    except Exception:
        pass

    if not title:
        try:
            title = _clean(
                await title_element.get_attribute("title")
            )
        except Exception:
            pass

    if not title:
        try:
            title = _clean(
                await title_element.inner_text()
            )
        except Exception:
            pass

    if not title:
        return None

    # Sometimes aria-label becomes:
    # "Software Engineer - job post"
    if title.lower().endswith(" - job post"):
        title = title[:-11].strip()

    # --------------------------------------------------------
    # Job URL
    # --------------------------------------------------------

    href = None
    job_key = None

    try:
        href = await title_element.get_attribute("href")
    except Exception:
        pass

    try:
        job_key = await title_element.get_attribute("data-jk")
    except Exception:
        pass

    if href:
        url = urljoin(BASE_URL, href)
    elif job_key:
        url = f"{BASE_URL}/viewjob?jk={job_key}"
    else:
        return None

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    company = await _safe_text(
        card,
        [
            "[data-testid='company-name']",
            "span[data-testid='company-name']",
            ".companyName",
            ".css-1h7lukg",
            "[data-company-name]",
        ],
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    location = await _safe_text(
        card,
        [
            "[data-testid='text-location']",
            "div[data-testid='text-location']",
            ".companyLocation",
            "[data-testid='job-location']",
        ],
    )

    # --------------------------------------------------------
    # Salary
    # --------------------------------------------------------

    salary = await _safe_text(
        card,
        [
            "[data-testid='attribute_snippet_testid']",
            "[data-testid='salary-snippet-container']",
            ".salary-snippet-container",
            ".salaryOnly",
            ".metadata.salary-snippet-container",
        ],
    )

    # --------------------------------------------------------
    # Description / snippet
    # --------------------------------------------------------

    description = await _safe_text(
        card,
        [
            "[data-testid='jobsnippet_footer']",
            "[data-testid='belowJobSnippet']",
            ".job-snippet",
            ".underShelfFooter",
            ".css-9446fg",
        ],
    )

    return {
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "url": url,
        "source": "indeed",
        "skill_query": skill,
        "description": description,
    }


# ---------------------------------------------------------------------------
# Find job cards
# ---------------------------------------------------------------------------

async def _get_job_cards(page):
    """
    Try several current/older Indeed card selectors.
    """

    selectors = [
        "div.job_seen_beacon",
        ".job_seen_beacon",
        ".tapItem",
        "li.css-5lfssm",
        "div.cardOutline",
    ]

    for selector in selectors:

        try:
            cards = await page.query_selector_all(selector)
        except Exception:
            cards = []

        if cards:
            logger.info(
                "[Indeed] Using card selector '%s' — %s card(s)",
                selector,
                len(cards),
            )

            return cards

    return []


# ---------------------------------------------------------------------------
# One skill
# ---------------------------------------------------------------------------

async def scrape_one_skill_indeed(
    skill: str,
    max_jobs: int,
    page,
) -> list[dict]:
    """
    Scrape Indeed jobs for one search query.

    `page` belongs to the caller.
    """

    jobs: list[dict] = []
    seen: set[str] = set()

    if max_jobs <= 0:
        return jobs

    # Indeed commonly returns around 15 jobs/page.
    pages_needed = max(
        1,
        (max_jobs + 14) // 15,
    )

    encoded_skill = quote_plus(skill)

    for page_number in range(pages_needed):

        if len(jobs) >= max_jobs:
            break

        start = page_number * 10

        url = (
            f"{SEARCH_URL}"
            f"?q={encoded_skill}"
            f"&l=India"
            f"&start={start}"
        )

        logger.info(
            "[Indeed] Fetching skill='%s', page=%s",
            skill,
            page_number + 1,
        )

        logger.info(
            "[Indeed] URL: %s",
            url,
        )

        try:

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            if response:
                logger.info(
                    "[Indeed] HTTP status: %s",
                    response.status,
                )

            # Give JS time to create cards.
            await asyncio.sleep(
                random.uniform(
                    4.0,
                    6.0,
                )
            )

            # --------------------------------------------------
            # Anti-bot check
            # --------------------------------------------------

            if await _page_is_blocked(page):

                logger.warning(
                    "[Indeed] Indeed blocked/challenged the browser but continue "
                    "for skill '%s'.",
                    skill,
                )

                try:
                    logger.warning(
                        "[Indeed] Current URL: %s",
                        page.url,
                    )
                except Exception:
                    pass

                

            # --------------------------------------------------
            # Cards
            # --------------------------------------------------

            cards = await _get_job_cards(page)

            # --------------------------------------------------
            # Fallback:
            # Sometimes wrapper classes change completely.
            # Find title anchors and use nearest container.
            # --------------------------------------------------

            if not cards:

                logger.warning(
                    "[Indeed] Standard card selectors returned 0. "
                    "Trying title-anchor fallback."
                )

                anchors = await page.query_selector_all(
                    "a.jcs-JobTitle, "
                    "h2.jobTitle a, "
                    "h2 a[data-jk], "
                    "a[data-jk]"
                )

                logger.info(
                    "[Indeed] Found %s potential title anchor(s)",
                    len(anchors),
                )

                for anchor in anchors:

                    if len(jobs) >= max_jobs:
                        break

                    try:

                        title = _clean(
                            await anchor.get_attribute(
                                "aria-label"
                            )
                        )

                        if not title:
                            title = _clean(
                                await anchor.get_attribute(
                                    "title"
                                )
                            )

                        if not title:
                            title = _clean(
                                await anchor.inner_text()
                            )

                        if not title:
                            continue

                        if title.lower().endswith(
                            " - job post"
                        ):
                            title = title[:-11].strip()

                        href = await anchor.get_attribute(
                            "href"
                        )

                        jk = await anchor.get_attribute(
                            "data-jk"
                        )

                        if href:
                            job_url = urljoin(
                                BASE_URL,
                                href,
                            )

                        elif jk:
                            job_url = (
                                f"{BASE_URL}"
                                f"/viewjob?jk={jk}"
                            )

                        else:
                            continue

                        if job_url in seen:
                            continue

                        seen.add(job_url)

                        jobs.append(
                            {
                                "title": title,
                                "company": None,
                                "location": None,
                                "salary": None,
                                "url": job_url,
                                "source": "indeed",
                                "skill_query": skill,
                                "description": None,
                            }
                        )

                    except Exception as exc:
                        logger.debug(
                            "[Indeed] Anchor fallback error: %s",
                            exc,
                        )

                if not anchors:
                    try:
                        logger.warning(
                            "[Indeed] Page title: %s",
                            await page.title(),
                        )

                        logger.warning(
                            "[Indeed] Final URL: %s",
                            page.url,
                        )

                    except Exception:
                        pass

                    break

            # --------------------------------------------------
            # Normal card extraction
            # --------------------------------------------------

            else:

                logger.info(
                    "[Indeed] Processing %s job card(s)",
                    len(cards),
                )

                for card in cards:

                    if len(jobs) >= max_jobs:
                        break

                    try:

                        job = await _extract_card(
                            card,
                            skill,
                        )

                        if not job:
                            continue

                        dedupe_key = (
                            job.get("url")
                            or
                            (
                                f"{job.get('title', '')}|"
                                f"{job.get('company', '')}"
                            )
                        )

                        if dedupe_key in seen:
                            continue

                        seen.add(
                            dedupe_key
                        )

                        jobs.append(
                            job
                        )

                    except Exception as exc:

                        logger.debug(
                            "[Indeed] Card extraction error: %s",
                            exc,
                        )

        except PWTimeout:

            logger.warning(
                "[Indeed] Timeout loading %s",
                url,
            )

        except Exception as exc:

            logger.exception(
                "[Indeed] Error scraping skill '%s': %s",
                skill,
                exc,
            )

        # Pause before next results page.
        if page_number < pages_needed - 1:

            await asyncio.sleep(
                random.uniform(
                    MIN_DELAY,
                    MAX_DELAY,
                )
            )

    logger.info(
        "[Indeed] Scraped %s job(s) for skill '%s'",
        len(jobs),
        skill,
    )

    return jobs


# ---------------------------------------------------------------------------
# Standalone wrapper
# ---------------------------------------------------------------------------

async def scrape_indeed(
    skills: list[str],
    max_per_skill: int = 10,
) -> list[dict]:

    all_jobs: list[dict] = []

    async with async_playwright() as pw:

        browser = await pw.firefox.launch(
            headless=False
        )

        page = await browser.new_page()

        try:
            for skill in skills:

                try:
                    jobs = await scrape_one_skill_indeed(
                        skill=skill,
                        max_jobs=max_per_skill,
                        page=page,
                    )

                    all_jobs.extend(jobs)

                except Exception as exc:
                    logger.exception(
                        "[Indeed] Failed skill '%s': %s",
                        skill,
                        exc,
                    )

                await asyncio.sleep(
                    random.uniform(
                        MIN_DELAY,
                        MAX_DELAY,
                    )
                )

        finally:
            await browser.close()

    logger.info(
        "[Indeed] Total scraped jobs: %s",
        len(all_jobs),
    )

    return all_jobs