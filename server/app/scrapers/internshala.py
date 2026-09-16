"""
CareerSync Internshala scraper - CLEAN MATCHING VERSION

This version deliberately separates:
- real job/internship description
- actual Skill(s) required
- eligibility text

It STOPS before Internshala's:
    "Earn certifications in these skills"

Therefore training links such as:
    Learn VLSI
    Learn React
    Learn Git & Github
    Learn AI in Data Science
do NOT enter Required / Key Skills and do NOT contaminate the job embedding.

Returned description format:

    Job Description:
    ...

    Required / Key Skills:
    MS SQL Server, SQL

    Eligibility:
    ...

skill_query remains discovery metadata only.
"""

import asyncio
import re
from typing import Iterable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag


_BASE = "https://internshala.com"
_DETAIL_DELAY = 0.7

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://internshala.com/",
}


_CERTIFICATION_MARKERS = (
    "earn certifications in these skills",
    "earn certification in these skills",
    "learn these skills",
)

_NEXT_SECTION_MARKERS = (
    "who can apply",
    "perks",
    "additional information",
    "number of openings",
    "about the company",
)

_NON_SKILLS = {
    "certificate",
    "letter of recommendation",
    "flexible work hours",
    "informal dress code",
    "5 days a week",
    "free snacks & beverages",
    "free snacks and beverages",
    "health insurance",
    "life insurance",
    "job offer",
    "work from home",
    "apply now",
    "start date",
    "duration",
    "stipend",
}


_CANONICAL_ALIASES = {
    "react": "React.js",
    "react js": "React.js",
    "react.js": "React.js",
    "node": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "expressjs": "Express.js",
    "express js": "Express.js",
    "express.js": "Express.js",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "ms sql server": "MS SQL Server",
    "sql server": "MS SQL Server",
    "mssql": "MS SQL Server",
    "sql": "SQL",
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "git": "Git",
    "github": "GitHub",
    "html": "HTML",
    "css": "CSS",
    "tailwind css": "Tailwind CSS",
    "redux": "Redux",
    "next.js": "Next.js",
    "next js": "Next.js",
    "angular": "Angular",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "rest api": "REST API",
    "graphql": "GraphQL",
    "selenium": "Selenium",
    "machine learning": "Machine Learning",
    "data science": "Data Science",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "excel": "Excel",
    "ms excel": "Excel",
}


def _slugify(skill: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        skill.strip().lower(),
    ).strip("-")


def _clean(value: str | None) -> str:
    if not value:
        return ""

    value = str(value).replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n", value)

    return value.strip()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []

    for value in values:
        value = _clean(value)

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def _normalize_skill(value: str) -> str | None:
    value = _clean(value)

    if not value or len(value) > 70:
        return None

    low = value.casefold().strip(" .,:;|-")

    if low in _NON_SKILLS:
        return None

    if low.startswith("learn "):
        return None

    if any(marker in low for marker in _CERTIFICATION_MARKERS):
        return None

    if any(marker in low for marker in _NEXT_SECTION_MARKERS):
        return None

    if low in {
        "skill(s) required",
        "skills required",
        "key skills",
        "+ 5 more skills",
        "+5 more skills",
    }:
        return None

    # Never let company/search words like plain "Express" become Express.js.
    if low == "express":
        return None

    # Reject sentence-like text.
    if len(value.split()) > 6:
        return None

    return _CANONICAL_ALIASES.get(low, value)


def _clean_skill_list(values: Iterable[str]) -> list[str]:
    result = []

    for value in values:
        normalized = _normalize_skill(value)

        if normalized:
            result.append(normalized)

    return _dedupe(result)


def _parse_cards(
    soup: BeautifulSoup,
    skill_query: str,
) -> list[dict]:
    jobs = []

    for card in soup.select(".individual_internship"):
        try:
            title_tag = (
                card.select_one(".job-internship-name a")
                or card.select_one(".profile a")
            )

            if not title_tag:
                continue

            title = _clean(
                title_tag.get_text(" ", strip=True)
            )

            if not title:
                continue

            company_tag = (
                card.select_one(".company_name a")
                or card.select_one(".company-name")
            )

            location_tag = (
                card.select_one(".location_link")
                or card.select_one(".locations span")
            )

            salary_tag = (
                card.select_one(".stipend")
                or card.select_one(".salary")
            )

            href = title_tag.get("href")
            url = urljoin(_BASE, href) if href else None

            jobs.append(
                {
                    "title": title,
                    "company": (
                        _clean(
                            company_tag.get_text(
                                " ",
                                strip=True,
                            )
                        )
                        if company_tag
                        else None
                    ),
                    "location": (
                        _clean(
                            location_tag.get_text(
                                " ",
                                strip=True,
                            )
                        )
                        if location_tag
                        else None
                    ),
                    "salary": (
                        _clean(
                            salary_tag.get_text(
                                " ",
                                strip=True,
                            )
                        )
                        if salary_tag
                        else None
                    ),
                    "url": url,
                    "source": "internshala",
                    "skill_query": skill_query,
                    "description": None,
                }
            )

        except Exception as exc:
            print(
                f"[Internshala] Card skipped: {exc}"
            )

    return jobs


def _find_heading(
    soup: BeautifulSoup,
    texts: tuple[str, ...],
) -> Tag | None:
    for tag in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "div", "span"]
    ):
        text = _clean(
            tag.get_text(" ", strip=True)
        )

        if not text or len(text) > 140:
            continue

        low = text.casefold()

        if any(
            expected.casefold() in low
            for expected in texts
        ):
            return tag

    return None


def _extract_about_description(
    soup: BeautifulSoup,
) -> str:
    selectors = [
        "#about_internship .text-container",
        "#about_job .text-container",
        ".about_internship .text-container",
        ".about_job .text-container",
        "[id*='about_internship'] .text-container",
        "[id*='about_job'] .text-container",
    ]

    candidates = []

    for selector in selectors:
        for el in soup.select(selector):
            text = _clean(
                el.get_text("\n", strip=True)
            )

            if len(text) >= 80:
                candidates.append(text)

    if candidates:
        description = max(
            candidates,
            key=len,
        )

        # Defensive cleanup in case the container also includes later
        # Internshala sections.
        lower = description.casefold()
        cuts = []

        for marker in (
            "skill(s) required",
            "skills required",
            "who can apply",
            "perks",
            "earn certifications in these skills",
        ):
            pos = lower.find(marker)

            if pos != -1:
                cuts.append(pos)

        if cuts:
            description = description[: min(cuts)]

        return _clean(description)

    heading = _find_heading(
        soup,
        (
            "about the work from home job/internship",
            "about the work from home internship",
            "about the job/internship",
            "about the internship",
            "about the job",
        ),
    )

    if not heading:
        return ""

    parts = []

    for node in heading.find_all_next(
        ["p", "li", "div", "h2", "h3", "h4"],
        limit=100,
    ):
        text = _clean(
            node.get_text(" ", strip=True)
        )

        if not text:
            continue

        low = text.casefold()

        if (
            "skill(s) required" in low
            or "skills required" in low
            or "who can apply" in low
            or "perks" == low
            or any(
                marker in low
                for marker in _CERTIFICATION_MARKERS
            )
        ):
            break

        if node.name in {"p", "li"}:
            parts.append(text)

    return _clean(
        "\n".join(
            _dedupe(parts)
        )
    )


def _extract_required_skills(
    soup: BeautifulSoup,
) -> list[str]:
    """
    STRICT extraction:
    Start after the literal Skill(s) required heading and STOP before
    "Earn certifications in these skills".

    This prevents Internshala course suggestions from entering the job's
    required-skill list.
    """
    heading = _find_heading(
        soup,
        (
            "skill(s) required",
            "skills required",
        ),
    )

    if not heading:
        return []

    raw_skills = []

    # First: inspect elements in document order after the heading.
    for node in heading.find_all_next(
        ["h2", "h3", "h4", "h5", "div", "span", "a", "li", "button"],
        limit=120,
    ):
        text = _clean(
            node.get_text(" ", strip=True)
        )

        if not text:
            continue

        low = text.casefold()

        # Hard stop BEFORE training/certification links.
        if any(
            marker in low
            for marker in _CERTIFICATION_MARKERS
        ):
            break

        if any(
            marker == low
            or low.startswith(marker)
            for marker in _NEXT_SECTION_MARKERS
        ):
            break

        classes = " ".join(
            node.get("class", [])
        ).casefold()

        # Prefer Internshala skill chips / compact link-like elements.
        looks_like_skill_chip = (
            "round_tabs" in classes
            or "round-tab" in classes
            or "skill" in classes
            or node.name in {"a", "button"}
        )

        if not looks_like_skill_chip:
            continue

        normalized = _normalize_skill(text)

        if normalized:
            raw_skills.append(normalized)

    skills = _dedupe(raw_skills)

    if skills:
        return skills

    # Fallback: only inspect the smallest useful parent around the heading.
    parent = heading.parent

    if parent:
        parent_text = _clean(
            parent.get_text("\n", strip=True)
        )

        # Cut at certification section before parsing.
        lower = parent_text.casefold()
        cuts = []

        for marker in (
            *_CERTIFICATION_MARKERS,
            *_NEXT_SECTION_MARKERS,
        ):
            pos = lower.find(marker)

            if pos != -1:
                cuts.append(pos)

        if cuts:
            parent_text = parent_text[: min(cuts)]

        # Remove the heading itself.
        parent_text = re.sub(
            r"skill\(s\)\s+required",
            "",
            parent_text,
            flags=re.IGNORECASE,
        )
        parent_text = re.sub(
            r"skills\s+required",
            "",
            parent_text,
            flags=re.IGNORECASE,
        )

        # Split conservative delimiters only.
        candidates = re.split(
            r"[\n,|•]+",
            parent_text,
        )

        skills = _clean_skill_list(candidates)

    return skills


def _extract_who_can_apply(
    soup: BeautifulSoup,
) -> str:
    heading = _find_heading(
        soup,
        ("who can apply",),
    )

    if not heading:
        return ""

    parts = []

    for node in heading.find_all_next(
        ["p", "li", "div", "h2", "h3", "h4"],
        limit=60,
    ):
        text = _clean(
            node.get_text(" ", strip=True)
        )

        if not text:
            continue

        low = text.casefold()

        if (
            low == "perks"
            or low.startswith("perks")
            or low.startswith("additional information")
            or low.startswith("number of openings")
            or low.startswith("about the company")
        ):
            break

        if node.name in {"p", "li"}:
            parts.append(text)

    return _clean(
        "\n".join(
            _dedupe(parts)
        )
    )


def _build_description(
    full_jd: str,
    skills: list[str],
    eligibility: str,
) -> str | None:
    """
    Stable format for downstream matching.
    """
    parts = []

    if full_jd:
        parts.append(
            "Job Description:\n" + full_jd.strip()
        )

    if skills:
        parts.append(
            "Required / Key Skills:\n"
            + ", ".join(skills)
        )

    if eligibility:
        parts.append(
            "Eligibility:\n" + eligibility.strip()
        )

    return "\n\n".join(parts).strip() or None


async def _enrich_job(
    client: httpx.AsyncClient,
    job: dict,
) -> dict:
    url = job.get("url")

    if not url:
        return job

    try:
        response = await client.get(url)

        if response.status_code != 200:
            print(
                f"[Internshala] Detail HTTP "
                f"{response.status_code}: {url}"
            )
            return job

        soup = BeautifulSoup(
            response.text,
            "lxml",
        )

        full_jd = _extract_about_description(soup)
        skills = _extract_required_skills(soup)
        eligibility = _extract_who_can_apply(soup)

        job["key_skills"] = skills

        job["description"] = _build_description(
            full_jd,
            skills,
            eligibility,
        )

        print(
            f"[Internshala] Cleaned | "
            f"{job.get('title')} | "
            f"skills={skills}"
        )

    except Exception as exc:
        print(
            f"[Internshala] Detail extraction failed "
            f"for {url}: {exc}"
        )

    return job


def _job_key(job: dict) -> str:
    url = (job.get("url") or "").strip()

    if url:
        return url.rstrip("/").casefold()

    return (
        f"{job.get('title') or ''}|"
        f"{job.get('company') or ''}|"
        f"{job.get('location') or ''}"
    ).casefold()


def _next_page_url(
    soup: BeautifulSoup,
    current_url: str,
) -> str | None:
    rel_next = soup.select_one('a[rel="next"]')

    if rel_next and rel_next.get("href"):
        return urljoin(
            current_url,
            rel_next.get("href"),
        )

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        text = _clean(
            anchor.get_text(
                " ",
                strip=True,
            )
        ).casefold()

        aria = str(
            anchor.get("aria-label") or ""
        ).casefold()

        title = str(
            anchor.get("title") or ""
        ).casefold()

        if (
            text in {"next", "next page", "›", "»"}
            or "next" in aria
            or "next" in title
        ):
            return urljoin(
                current_url,
                anchor.get("href"),
            )

    return None


async def scrape_internshala(
    skills: list[str],
    max_per_skill: int = 5,
) -> list[dict]:
    all_jobs = []
    seen_global: set[str] = set()

    async with httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:

        for skill_query in skills:
            collected = []
            slug = _slugify(skill_query)

            start_urls = [
                f"{_BASE}/jobs/keywords-{slug}/",
                f"{_BASE}/internships/keywords-{slug}/",
            ]

            for initial_url in start_urls:
                if len(collected) >= max_per_skill:
                    break

                current_url = initial_url
                visited_pages = set()

                while (
                    current_url
                    and len(collected) < max_per_skill
                ):
                    if current_url in visited_pages:
                        break

                    visited_pages.add(current_url)

                    try:
                        print(
                            f"[Internshala] Fetching: "
                            f"{current_url} | "
                            f"query={skill_query} | "
                            f"{len(collected)}/{max_per_skill}"
                        )

                        response = await client.get(
                            current_url
                        )

                        if response.status_code != 200:
                            print(
                                f"[Internshala] Search HTTP "
                                f"{response.status_code}: "
                                f"{current_url}"
                            )
                            break

                        soup = BeautifulSoup(
                            response.text,
                            "lxml",
                        )

                        parsed = _parse_cards(
                            soup,
                            skill_query,
                        )

                        for job in parsed:
                            if (
                                len(collected)
                                >= max_per_skill
                            ):
                                break

                            key = _job_key(job)

                            if key in seen_global:
                                continue

                            enriched = await _enrich_job(
                                client,
                                job,
                            )

                            seen_global.add(key)
                            collected.append(enriched)
                            all_jobs.append(enriched)

                            print(
                                f"[Internshala] Accepted "
                                f"{len(collected)}/"
                                f"{max_per_skill} | "
                                f"{skill_query} | "
                                f"{enriched.get('title')}"
                            )

                            await asyncio.sleep(
                                _DETAIL_DELAY
                            )

                        if (
                            len(collected)
                            < max_per_skill
                        ):
                            current_url = _next_page_url(
                                soup,
                                current_url,
                            )
                        else:
                            break

                    except Exception as exc:
                        print(
                            f"[Internshala] Page failed "
                            f"{current_url}: {exc}"
                        )
                        break

            print(
                f"[Internshala] FINAL | "
                f"{skill_query} -> "
                f"{len(collected)}/"
                f"{max_per_skill} unique jobs"
            )

    print(
        f"[Internshala] TOTAL UNIQUE JOBS "
        f"RETURNED: {len(all_jobs)}"
    )

    return all_jobs
