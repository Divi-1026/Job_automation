"""
Internshala job scraper.

Hits internshala.com/jobs search pages and parses the HTML job cards.
Returns a list of plain dicts — no DB dependency here.
"""
import re
import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://internshala.com/",
}

_BASE = "https://internshala.com"


def _slugify(skill: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", skill.strip().lower()).strip("-")


def _parse_cards(soup: BeautifulSoup, skill: str) -> list[dict]:
    jobs = []

    # Internshala uses .individual_internship containers for both jobs & internships
    for card in soup.select(".individual_internship"):
        try:
            title_tag = card.select_one(".job-internship-name a") or card.select_one(".profile a")
            company_tag = card.select_one(".company_name a") or card.select_one(".company-name")
            loc_tag = card.select_one(".location_link") or card.select_one(".locations span")
            salary_tag = card.select_one(".stipend") or card.select_one(".salary")

            title   = title_tag.get_text(strip=True)   if title_tag   else None
            company = company_tag.get_text(strip=True) if company_tag else None
            location = loc_tag.get_text(strip=True)    if loc_tag     else None
            salary  = salary_tag.get_text(strip=True)  if salary_tag  else None

            href = title_tag["href"] if title_tag and title_tag.get("href") else None
            url  = (_BASE + href) if href and href.startswith("/") else href

            if title:
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "salary":      salary,
                    "url":         url,
                    "source":      "internshala",
                    "skill_query": skill,
                    "description": None,
                })
        except Exception:
            continue

    return jobs


async def scrape_internshala(skills: list[str], max_per_skill: int = 10) -> list[dict]:
    """Return up to `max_per_skill` jobs per skill from Internshala."""
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(
        headers=_HEADERS, follow_redirects=True, timeout=30.0
    ) as client:
        for skill in skills:
            slug = _slugify(skill)
            urls_to_try = [
                f"{_BASE}/jobs/keywords-{slug}/",
                f"{_BASE}/internships/keywords-{slug}/",
            ]
            for page_url in urls_to_try:
                try:
                    resp = await client.get(page_url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "lxml")
                    parsed = _parse_cards(soup, skill)
                    count = 0
                    for job in parsed:
                        if count >= max_per_skill:
                            break
                        key = job.get("url") or f"{job['title']}|{job['company']}"
                        if key not in seen_urls:
                            seen_urls.add(key)
                            all_jobs.append(job)
                            count += 1
                except Exception:
                    continue

    return all_jobs
