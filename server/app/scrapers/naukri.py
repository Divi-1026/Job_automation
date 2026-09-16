"""
CareerSync Naukri scraper — JD-first trustworthy matching version.

TRUST RULES
-----------
Exact skill coverage uses ONLY technical/core skills extracted from the
ACTUAL CLEAN JOB DESCRIPTION.

Naukri "Key Skills" / platform tags are NEVER treated as required skills.
They are preserved only as semantic context.

We intentionally DO NOT depend on Naukri's visual preferred/star marker,
because that UI signal is not stable enough to use as a scoring source.

Structured description:

Job Description:
<full clean employer JD>

Exact Required Skills:
<JD-extracted, evidence-validated technical/core skills>

JD Extracted Skills:
<same trustworthy JD skill list>

Platform Key Skills:
<Naukri platform tags; semantic-only>

Required Experience:
<experience>

skill_query remains discovery metadata only.
"""


from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Iterable
from app.core.config import settings
from bs4 import BeautifulSoup, Tag
from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

try:
    from playwright_stealth import Stealth
except Exception:
    Stealth = None

from app.utils.naukri_skill_extractor import extract_naukri_core_skills_batch
from app.utils.semantic_match import canonicalize_skill

# api_key = settings.GROQ_API_KEY
logger = logging.getLogger(__name__)

_BASE = "https://www.naukri.com"

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

_GENERIC_PLATFORM_TAGS = {
    "web application",
    "web application development",
    "web development",
    "frontend developer",
    "front end",
    "frontend",
    "backend developer",
    "back end",
    "backend",
    "software developer",
    "software development",
    "development",
    "programming",
    "programming languages",
    "coding",
    "coding standards",
    "architecture",
    "workflow",
    "workflow analysis",
    "native",
}

_STAR_CHARS = ("★", "☆", "⭐", "✩", "✪")

def _groq_api_key():
    try:
        from app.core.config import settings

        if settings.GROQ_API_KEY:
            return settings.GROQ_API_KEY
    except Exception:
        pass

    return os.getenv("GROQ_API_KEY")
api_key = _groq_api_key()

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


def _canonical_display(skill: str) -> str:
    canonical = canonicalize_skill(skill)
    if not canonical:
        return ""
    # canonicalize_skill uses lower-case canonical names intentionally.
    # Give common technology names readable display names.
    display = {
        "react.js": "React.js",
        "react": "React.js",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "node.js": "Node.js",
        "express.js": "Express.js",
        "html": "HTML",
        "css": "CSS",
        "tailwind css": "Tailwind CSS",
        "bootstrap": "Bootstrap",
        "jquery": "jQuery",
        "angular": "Angular",
        "angularjs": "AngularJS",
        "vue.js": "Vue.js",
        "next.js": "Next.js",
        "blazor": "Blazor",
        "asp.net": "ASP.NET",
        "c#": "C#",
        "c++": "C++",
        "java": "Java",
        "python": "Python",
        "sql": "SQL",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
        "mongodb": "MongoDB",
        "ms sql server": "MS SQL Server",
        "redis": "Redis",
        "rest api": "REST API",
        "graphql": "GraphQL",
        "json": "JSON",
        "xml": "XML",
        "git": "Git",
        "github": "GitHub",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "aws": "AWS",
        "azure": "Azure",
        "gcp": "GCP",
        "junit": "JUnit",
        "pytest": "PyTest",
        "selenium": "Selenium",
        "elasticsearch": "Elasticsearch",
        "ajax": "AJAX",
        "http": "HTTP",
    }
    return display.get(canonical, skill.strip())


def _clean_skill_values(values: Iterable[str], *, keep_generic: bool = True) -> list[str]:
    result = []
    for raw in values:
        raw = _clean(raw)
        if not raw:
            continue

        for char in _STAR_CHARS:
            raw = raw.replace(char, " ")
        raw = _clean(raw)

        if not raw or len(raw) > 80:
            continue
        if len(raw.split()) > 7:
            continue

        low = raw.casefold().strip(" .,:;-")
        if low == "express":
            # Never turn American Express / generic "express" into Express.js.
            continue
        if not keep_generic and low in _GENERIC_PLATFORM_TAGS:
            continue

        display = _canonical_display(raw)
        if display:
            result.append(display)

    return _dedupe(result)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _naukri_page_url(slug: str, page_no: int) -> str:
    if page_no <= 1:
        return f"{_BASE}/{slug}-jobs"
    return f"{_BASE}/{slug}-jobs-{page_no}"


def _job_key(job: dict) -> str:
    url = _clean(job.get("url"))
    if url:
        return url.rstrip("/").casefold()
    return (
        f"{job.get('title') or ''}|"
        f"{job.get('company') or ''}|"
        f"{job.get('location') or ''}"
    ).casefold()


async def _extract_card(card, skill_query: str) -> dict | None:
    title_el = await card.query_selector(".title")
    if not title_el:
        return None

    title = _clean(await title_el.inner_text())
    if not title:
        return None

    company_el = await card.query_selector(".comp-name")
    loc_el = await card.query_selector(".loc-wrap")
    sal_el = await card.query_selector(".sal-wrap")
    exp_el = await card.query_selector(".exp-wrap")

    url = await title_el.get_attribute("href")

    return {
        "title": title,
        "company": _clean(await company_el.inner_text()) if company_el else None,
        "location": _clean(await loc_el.inner_text()) if loc_el else None,
        "salary": _clean(await sal_el.inner_text()) if sal_el else None,
        "url": url,
        "source": "naukri",
        "skill_query": skill_query,
        "_listing_experience": _clean(await exp_el.inner_text()) if exp_el else None,
    }


def _extract_clean_jd(soup: BeautifulSoup) -> str:
    selectors = [
        ".styles_JDC__dang-inner-html__h0K4t",
        ".styles_job-desc-container__txpYf",
        ".job-desc",
        ".dang-inner-html",
        "[class*='job-desc']",
        "[class*='jobDescription']",
        "[class*='JDC'] [class*='dang-inner-html']",
    ]

    candidates = []
    for selector in selectors:
        for node in soup.select(selector):
            text = _clean(node.get_text("\n", strip=True))
            if len(text) >= 40:
                candidates.append(text)

    if not candidates:
        return ""

    text = max(candidates, key=len)

    # Stop before Naukri metadata that is not part of the JD body.
    lower = "\n" + text.casefold()
    cuts = []
    for marker in (
        "\nrole:",
        "\nindustry type:",
        "\ndepartment:",
        "\nemployment type:",
        "\nrole category:",
        "\neducation",
        "\nkey skills",
        "\nabout company",
    ):
        pos = lower.find(marker)
        if pos != -1:
            cuts.append(max(0, pos - 1))

    if cuts:
        text = text[: min(cuts)]

    text = re.sub(
        r"^\s*job\s+description\s*:?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return _clean(text)


def _is_preferred_chip(node: Tag) -> bool:
    """
    Detect Naukri's star-marked preferred keyskill.

    We deliberately use several signals because Naukri changes HTML classes:
    - literal star character in chip/parent text
    - class/id/title/aria-label containing star/preferred
    - SVG/icon metadata containing star/preferred
    """
    current = node
    for _ in range(3):
        if not isinstance(current, Tag):
            break

        text = _clean(current.get_text(" ", strip=True))
        if any(star in text for star in _STAR_CHARS):
            return True

        attrs = " ".join(
            [
                str(current.get("class") or ""),
                str(current.get("id") or ""),
                str(current.get("title") or ""),
                str(current.get("aria-label") or ""),
                str(current.get("data-title") or ""),
            ]
        ).casefold()

        if "preferred" in attrs or "star" in attrs:
            return True

        for icon in current.find_all(["svg", "i", "span"], recursive=True):
            icon_meta = " ".join(
                [
                    str(icon.get("class") or ""),
                    str(icon.get("title") or ""),
                    str(icon.get("aria-label") or ""),
                    str(icon.get("data-icon") or ""),
                ]
            ).casefold()
            if "preferred" in icon_meta or "star" in icon_meta:
                return True

        current = current.parent

    return False


def _find_key_skill_container(soup: BeautifulSoup) -> Tag | None:
    # Strong class selectors first.
    for selector in (
        ".key-skill",
        ".styles_key-skill__GIPn_",
        "[class*='key-skill']",
        "[class*='keySkill']",
        "[class*='keySkills']",
    ):
        node = soup.select_one(selector)
        if node:
            return node

    # Fallback: locate heading and take nearest useful parent.
    for heading in soup.find_all(["h2", "h3", "h4", "div", "span"]):
        text = _clean(heading.get_text(" ", strip=True)).casefold()
        if text == "key skills" or text.startswith("key skills "):
            return heading.parent if isinstance(heading.parent, Tag) else heading

    return None



async def _extract_naukri_keyskills_live(page) -> tuple[list[str], list[str], list[dict]]:
    """
    Read Naukri Key Skills from the LIVE browser DOM.

    Why live DOM instead of only BeautifulSoup?
    --------------------------------------------
    Naukri can render the preferred-keyskill star through:
      - SVG / icon elements
      - CSS pseudo-elements (::before / ::after)
      - class / aria / title metadata

    Those visual signals may disappear when page HTML is converted to plain
    text. This function inspects the real rendered DOM and computed styles.

    Returns:
        preferred_star_skills, normal_platform_keyskills, debug_rows
    """
    js = r"""
    () => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const low = s => norm(s).toLowerCase();

      function attrDump(el) {
        if (!el || !el.getAttributeNames) return '';
        return el.getAttributeNames()
          .map(n => `${n}=${el.getAttribute(n) || ''}`)
          .join(' ');
      }

      function pseudoDump(el) {
        if (!el) return '';
        let out = [];
        for (const pseudo of ['::before', '::after']) {
          try {
            const cs = getComputedStyle(el, pseudo);
            const c = (cs && cs.content) ? cs.content : '';
            if (c && c !== 'none' && c !== 'normal' && c !== '""') out.push(c);
          } catch (_) {}
        }
        return out.join(' ');
      }

      function preferredSignal(el) {
        let node = el;
        for (let depth = 0; node && depth < 4; depth++, node = node.parentElement) {
          const txt = norm(node.innerText || node.textContent || '');
          const html = norm(node.innerHTML || '');
          const attrs = attrDump(node);
          const pseudo = pseudoDump(node);
          const blob = `${txt} ${attrs} ${pseudo} ${html}`.toLowerCase();

          if (
            /[★☆⭐✩✪]/.test(`${txt} ${pseudo}`) ||
            /\bpreferred\b/.test(blob) ||
            /\bstar(?:red)?\b/.test(blob) ||
            /icon[-_ ]?star/.test(blob) ||
            /star[-_ ]?icon/.test(blob)
          ) return { preferred: true, signal: blob.slice(0, 700) };

          // Also inspect immediate siblings; the star is sometimes a sibling
          // icon next to the actual skill text.
          for (const sib of [node.previousElementSibling, node.nextElementSibling]) {
            if (!sib) continue;
            const sblob = `${norm(sib.innerText || sib.textContent || '')} ${attrDump(sib)} ${pseudoDump(sib)} ${norm(sib.innerHTML || '')}`.toLowerCase();
            if (
              /[★☆⭐✩✪]/.test(sblob) ||
              /\bpreferred\b/.test(sblob) ||
              /\bstar(?:red)?\b/.test(sblob) ||
              /icon[-_ ]?star/.test(sblob) ||
              /star[-_ ]?icon/.test(sblob)
            ) return { preferred: true, signal: sblob.slice(0, 700) };
          }
        }
        return { preferred: false, signal: '' };
      }

      // Find the Key Skills section by heading text first.
      let heading = [...document.querySelectorAll('h2,h3,h4,h5,div,span')]
        .find(el => {
          const t = low(el.innerText || el.textContent || '');
          return t === 'key skills' || t.startsWith('key skills ');
        });

      // Fallback to common Naukri containers.
      let container =
        heading?.parentElement ||
        document.querySelector("[class*='key-skill']") ||
        document.querySelector("[class*='keySkill']") ||
        document.querySelector("[class*='keySkills']");

      if (!container) return [];

      // Widen the section carefully so we include chips but stop before
      // Education / Company Profile.
      let section = container;
      for (let i = 0; i < 3 && section.parentElement; i++) {
        const txt = low(section.innerText || section.textContent || '');
        if (txt.includes('key skills') && txt.length < 2500) {
          section = section.parentElement;
        } else {
          break;
        }
      }

      const els = [...section.querySelectorAll('a,span,li,button,div')];
      const rows = [];
      const seen = new Set();

      for (const el of els) {
        const text = norm(el.innerText || el.textContent || '');
        const t = text.toLowerCase();

        if (!text || text.length > 90) continue;
        if (t === 'key skills' || t === 'skills') continue;
        if (t.includes('skills highlighted with') || t.includes('preferred keyskills')) continue;
        if (t.startsWith('education') || t.startsWith('company profile')) continue;

        // Skip wrappers that contain multiple candidate child texts.
        const directChildren = [...el.children]
          .map(c => norm(c.innerText || c.textContent || ''))
          .filter(Boolean);
        if (directChildren.length >= 2 && new Set(directChildren).size >= 2) continue;

        // Skill-looking nodes. Naukri commonly uses links/spans; allow short
        // divs only if they have skill-like class metadata.
        const attrs = attrDump(el).toLowerCase();
        const isLikely =
          ['A','SPAN','LI','BUTTON'].includes(el.tagName) ||
          /skill|chip|tag/.test(attrs);
        if (!isLikely) continue;

        const key = text.toLowerCase();
        if (seen.has(key)) continue;

        const pref = preferredSignal(el);
        rows.push({
          text,
          preferred: pref.preferred,
          signal: pref.signal,
          tag: el.tagName,
          attrs: attrDump(el).slice(0, 400),
          before: pseudoDump(el).slice(0, 200),
        });
        seen.add(key);
      }

      return rows;
    }
    """

    try:
        rows = await page.evaluate(js)
    except Exception as exc:
        logger.warning("[Naukri] Live key-skill DOM extraction failed: %s", exc)
        return [], [], []

    preferred_raw = []
    normal_raw = []

    for row in rows or []:
        text = _clean((row or {}).get("text"))
        if not text:
            continue

        if (row or {}).get("preferred"):
            preferred_raw.append(text)
        else:
            normal_raw.append(text)

    preferred = _clean_skill_values(preferred_raw, keep_generic=True)
    preferred_keys = {canonicalize_skill(x) for x in preferred}

    normal = []
    for item in _clean_skill_values(normal_raw, keep_generic=True):
        if canonicalize_skill(item) not in preferred_keys:
            normal.append(item)

    return _dedupe(preferred), _dedupe(normal), rows or []


def _extract_naukri_keyskills(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Returns:
        preferred_star_skills, normal_platform_key_skills
    """
    container = _find_key_skill_container(soup)
    if not container:
        return [], []

    preferred = []
    normal = []

    # Chips are usually links/spans inside the key-skill section.
    candidates = container.find_all(["a", "span", "li", "button"], recursive=True)

    for node in candidates:
        text = _clean(node.get_text(" ", strip=True))
        if not text:
            continue

        low = text.casefold()
        if (
            low in {"key skills", "skills"}
            or "skills highlighted with" in low
            or "preferred keyskills" in low
            or len(text) > 80
        ):
            continue

        # Avoid parent wrappers that simply concatenate many child chips.
        child_texts = [
            _clean(child.get_text(" ", strip=True))
            for child in node.find_all(["a", "span", "li", "button"], recursive=False)
        ]
        child_texts = [x for x in child_texts if x]
        if len(child_texts) >= 2:
            continue

        is_preferred = _is_preferred_chip(node)
        cleaned = _clean_skill_values([text], keep_generic=True)
        if not cleaned:
            continue

        skill = cleaned[0]
        if is_preferred:
            preferred.append(skill)
        else:
            normal.append(skill)

    preferred = _dedupe(preferred)

    # A skill should not be duplicated in normal list if already starred.
    preferred_keys = {x.casefold() for x in preferred}
    normal = [
        x for x in _dedupe(normal)
        if x.casefold() not in preferred_keys
    ]

    return preferred, normal


def _parse_experience_range(value: str | None) -> str | None:
    """
    Parse only an explicit experience value such as:
      2 - 3 years
      4-7 Yrs
      5+ years
      Fresher

    IMPORTANT:
    We do not scan arbitrary page/JD text here because unrelated numeric
    ranges can be mistaken for experience.
    """
    text = _clean(value)
    if not text:
        return None

    if re.search(r"\\b(fresher|freshers|no experience)\\b", text, flags=re.IGNORECASE):
        return "0"

    match = re.search(
        r"(?<!\\d)(\\d+(?:\\.\\d+)?)\\s*(?:-|–|—|to)\\s*(\\d+(?:\\.\\d+)?)"
        r"\\s*(?:years?|yrs?)?\\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)}-{match.group(2)}"

    plus = re.search(
        r"(?<!\\d)(\\d+(?:\\.\\d+)?)\\s*\\+\\s*(?:years?|yrs?)?\\b",
        text,
        flags=re.IGNORECASE,
    )
    if plus:
        return f"{plus.group(1)}+"

    single = re.search(
        r"(?<!\\d)(\\d+(?:\\.\\d+)?)\\s*(?:years?|yrs?)\\b",
        text,
        flags=re.IGNORECASE,
    )
    if single:
        return single.group(1)

    return None


def _extract_title_experience(title: str | None) -> str | None:
    """
    Strong fallback/check for titles such as:
      React JS Developer - INF (2-3) YRS
    """
    title = _clean(title)
    if not title:
        return None

    match = re.search(
        r"\\(\\s*(\\d+(?:\\.\\d+)?)\\s*(?:-|–|—|to)\\s*"
        r"(\\d+(?:\\.\\d+)?)\\s*\\)\\s*(?:years?|yrs?)?\\b",
        title,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)}-{match.group(2)}"

    return None


def _extract_experience(
    soup: BeautifulSoup,
    listing_value: str | None,
    title: str | None = None,
) -> str | None:
    """
    Experience source priority:

      1. Search-result card's dedicated .exp-wrap value.
      2. Job title when it explicitly contains '(X-Y) YRS'.
      3. Detail-page dedicated experience selectors.

    The broad detail selector [class*='exp'] is intentionally removed because
    it can match unrelated elements and was capable of producing a wrong
    experience such as 4-7 for a Naukri job whose actual card says 2-3 years.
    """

    listing_raw = _clean(listing_value)
    listing_exp = _parse_experience_range(listing_raw)

    title_raw = _clean(title)
    title_exp = _extract_title_experience(title_raw)

    logger.info(
        "[Naukri][EXP] title=%r | listing_raw=%r | listing_parsed=%r | title_parsed=%r",
        title_raw,
        listing_raw,
        listing_exp,
        title_exp,
    )

    # The Naukri search card has a dedicated experience field, so trust it first.
    if listing_exp:
        if title_exp and title_exp != listing_exp:
            logger.warning(
                "[Naukri][EXP] MISMATCH | title=%r | listing=%r | "
                "Using LISTING experience because .exp-wrap is the dedicated "
                "Naukri experience field.",
                title_exp,
                listing_exp,
            )
        else:
            logger.info("[Naukri][EXP] USING LISTING experience=%s", listing_exp)

        return listing_exp

    # A title like '(2-3) YRS' is a strong fallback if the listing field is absent.
    if title_exp:
        logger.info("[Naukri][EXP] USING TITLE experience=%s", title_exp)
        return title_exp

    # Detail page: use only specific, experience-looking selectors.
    # Do NOT use broad [class*='exp'].
    detail_candidates = []

    for selector in (
        ".exp-wrap",
        "[class*='experience']",
    ):
        for node in soup.select(selector):
            raw = _clean(node.get_text(" ", strip=True))
            parsed = _parse_experience_range(raw)

            if parsed:
                detail_candidates.append((selector, raw, parsed))
                logger.info(
                    "[Naukri][EXP] detail candidate | selector=%s | raw=%r | parsed=%s",
                    selector,
                    raw,
                    parsed,
                )

    if detail_candidates:
        selector, raw, parsed = detail_candidates[0]
        logger.info(
            "[Naukri][EXP] USING DETAIL experience=%s | selector=%s | raw=%r",
            parsed,
            selector,
            raw,
        )
        return parsed

    logger.warning(
        "[Naukri][EXP] NO EXPERIENCE FOUND | title=%r | listing_raw=%r",
        title_raw,
        listing_raw,
    )
    return None


def _build_final_description(
    *,
    clean_jd: str,
    exact_skills: list[str],
    jd_skills: list[str],
    platform_key_skills: list[str],
    experience: str | None,
) -> str | None:
    parts = []

    if clean_jd:
        parts.append("Job Description:\n" + clean_jd)

    if exact_skills:
        parts.append("Exact Required Skills:\n" + ", ".join(exact_skills))

    if jd_skills:
        parts.append("JD Extracted Skills:\n" + ", ".join(jd_skills))

    # IMPORTANT: Naukri platform tags are semantic context ONLY.
    # They never enter the exact-skill denominator.
    if platform_key_skills:
        parts.append("Platform Key Skills:\n" + ", ".join(platform_key_skills))

    if experience:
        parts.append("Required Experience:\n" + experience)

    return "\n\n".join(parts).strip() or None


async def _enrich_detail(page, job: dict) -> dict:
    url = job.get("url")
    if not url:
        return job

    try:
        logger.info("[Naukri] Opening detail page: %s", url)
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        await asyncio.sleep(2.0)

        soup = BeautifulSoup(await page.content(), "lxml")
        clean_jd = _extract_clean_jd(soup)

        # We DO NOT use Naukri star/preferred markers for exact matching.
        # The Key Skills section is read only as semantic context.
        preferred_like, normal_platform = _extract_naukri_keyskills(soup)
        platform_keyskills = _dedupe([*preferred_like, *normal_platform])

        experience = _extract_experience(
            soup,
            job.get("_listing_experience"),
            job.get("title"),
        )

        logger.info(
            "[Naukri][EXP] FINAL EXPERIENCE | %s | listing=%r | saved=%r",
            job.get("title"),
            job.get("_listing_experience"),
            experience,
        )

        job["_clean_jd"] = clean_jd
        job["_platform_key_skills"] = platform_keyskills
        job["_experience"] = experience

        logger.info(
            "[Naukri] Detail parsed | %s | jd_chars=%d | platform_semantic=%s",
            job.get("title"),
            len(clean_jd or ""),
            platform_keyskills,
        )

        if not clean_jd:
            logger.warning(
                "[Naukri] Clean JD missing | %s | exact skills will stay empty "
                "instead of trusting platform tags.",
                job.get("title"),
            )

    except PWTimeout:
        logger.warning("[Naukri] Detail timeout: %s", url)
    except Exception as exc:
        logger.warning("[Naukri] Detail failed | %s | %s", url, exc)

    job.pop("_listing_experience", None)
    return job


async def _make_page(pw):
    browser = await pw.firefox.launch(headless=True)

    context = await browser.new_context(
        viewport=random.choice(_VIEWPORTS),
        user_agent=random.choice(_USER_AGENTS),
        locale="en-US",
        timezone_id="Asia/Kolkata",
    )

    if Stealth is not None:
        try:
            await Stealth().apply_stealth_async(context)
        except Exception as exc:
            logger.debug("[Naukri] Stealth unavailable: %s", exc)

    page = await context.new_page()

    try:
        await page.goto(_BASE, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(2.0)
    except Exception:
        pass

    return browser, page


async def _scrape_one_skill(
    skill_query: str,
    max_jobs: int,
    page,
    seen_global: set[str],
) -> list[dict]:
    slug = _slugify(skill_query)
    accepted = []
    detail_page = await page.context.new_page()

    try:
        for page_no in range(1, 11):
            if len(accepted) >= max_jobs:
                break

            url = _naukri_page_url(slug, page_no)
            logger.info(
                "[Naukri] Fetching %s | query=%s | %d/%d",
                url, skill_query, len(accepted), max_jobs,
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                await asyncio.sleep(3)

                try:
                    await page.wait_for_selector(".srp-jobtuple-wrapper", timeout=15_000)
                except PWTimeout:
                    break

                cards = await page.query_selector_all(".srp-jobtuple-wrapper")
                if not cards:
                    break

                for card in cards:
                    if len(accepted) >= max_jobs:
                        break

                    job = await _extract_card(card, skill_query)
                    if not job:
                        continue

                    key = _job_key(job)
                    if key in seen_global:
                        continue

                    job = await _enrich_detail(detail_page, job)

                    seen_global.add(key)
                    accepted.append(job)

                    logger.info(
                        "[Naukri] Accepted %d/%d | %s | %s",
                        len(accepted), max_jobs, skill_query, job.get("title"),
                    )
                    await asyncio.sleep(random.uniform(1.8, 3.2))

            except Exception as exc:
                logger.warning("[Naukri] Search page failed | %s | %s", url, exc)

    finally:
        await detail_page.close()

    return accepted


async def scrape_naukri(
    skills: list[str],
    max_per_skill: int = 5,
) -> list[dict]:
    """
    Scrape + JD skill extraction + final description construction.

    Groq failure never drops a job. The extractor automatically falls back to
    deterministic local technical-skill extraction.
    """
    all_jobs = []
    seen_global: set[str] = set()

    async with async_playwright() as pw:
        browser, page = await _make_page(pw)
        try:
            for skill_query in skills:
                jobs = await _scrape_one_skill(
                    skill_query=skill_query,
                    max_jobs=max_per_skill,
                    page=page,
                    seen_global=seen_global,
                )
                all_jobs.extend(jobs)
                await asyncio.sleep(random.uniform(1.5, 2.5))
        finally:
            await browser.close()

    if not all_jobs:
        return []

    # LLM sees ONLY clean JD, never platform keyskills/search keyword.
    jd_skill_lists = await extract_naukri_core_skills_batch(all_jobs)

    for job, jd_skills in zip(all_jobs, jd_skill_lists):
        # Exact skills come ONLY from the actual JD extractor.
        jd_skills = _clean_skill_values(jd_skills or [], keep_generic=False)
        exact_skills = _dedupe(jd_skills)

        # Naukri platform Key Skills are semantic-only context.
        platform_skills = _clean_skill_values(
            job.get("_platform_key_skills") or [],
            keep_generic=True,
        )

        job["description"] = _build_final_description(
            clean_jd=job.get("_clean_jd") or "",
            exact_skills=exact_skills,
            jd_skills=jd_skills,
            platform_key_skills=platform_skills,
            experience=job.get("_experience"),
        )

        # Debug/UI only. V2 tasks do not persist this extra field.
        job["key_skills"] = exact_skills

        logger.info(
            "[Naukri] FINAL | %s | experience=%r | exact_from_jd=%s | platform_semantic=%s",
            job.get("title"),
            job.get("_experience"),
            exact_skills,
            platform_skills,
        )

        if not exact_skills:
            logger.warning(
                "[Naukri] No trustworthy exact skills found in actual JD | %s | "
                "platform tags were NOT promoted to requirements.",
                job.get("title"),
            )

        for key in (
            "_clean_jd",
            "_platform_key_skills",
            "_experience",
        ):
            job.pop(key, None)

    logger.info("[Naukri] TOTAL UNIQUE JOBS RETURNED: %d", len(all_jobs))
    return all_jobs
