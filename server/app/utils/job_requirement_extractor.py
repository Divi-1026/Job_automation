"""
CareerSync V4 FALLBACK job requirement extraction.

Primary path is NOT this module. Structured Key Skills are used directly.

Fallback only:
    jobs with NO structured Key Skills -> Groq GPT-OSS 20B -> strict JSON schema

Fallback:
    deterministic local extraction per job.

Why batching:
    one request handles several jobs, reducing request-rate pressure.
    A conservative inter-batch delay also protects the free-tier TPM window.

The model EXTRACTS requirements only. Candidate scoring remains deterministic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Sequence

import httpx

from app.core.config import settings
from app.utils.semantic_match import canonicalize_skill, extract_known_skills

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_rate_lock = asyncio.Lock()
_last_request_started = 0.0


REQUIREMENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_title": {"type": "string"},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "preferred_skills": {"type": "array", "items": {"type": "string"}},
        "min_years_experience": {
            "anyOf": [{"type": "number"}, {"type": "null"}]
        },
        "max_years_experience": {
            "anyOf": [{"type": "number"}, {"type": "null"}]
        },
        "education_requirements": {
            "type": "array", "items": {"type": "string"}
        },
        "degree_fields": {"type": "array", "items": {"type": "string"}},
        "mandatory_requirements": {
            "type": "array", "items": {"type": "string"}
        },
        "preferred_requirements": {
            "type": "array", "items": {"type": "string"}
        },
        "location_requirements": {
            "type": "array", "items": {"type": "string"}
        },
        "work_authorization_requirements": {
            "type": "array", "items": {"type": "string"}
        },
        "extraction_confidence": {
            "type": "number", "minimum": 0, "maximum": 1
        },
    },
    "required": [
        "role_title",
        "required_skills",
        "preferred_skills",
        "min_years_experience",
        "max_years_experience",
        "education_requirements",
        "degree_fields",
        "mandatory_requirements",
        "preferred_requirements",
        "location_requirements",
        "work_authorization_requirements",
        "extraction_confidence",
    ],
    "additionalProperties": False,
}

BATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "input_id": {"type": "integer"},
                    "requirements": REQUIREMENTS_SCHEMA,
                },
                "required": ["input_id", "requirements"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["jobs"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """You are a precise job-requirement extraction API.

For EACH supplied job:
1. Use only its title and description. Never use the search/discovery keyword.
   Platform note:
   - For Naukri, description may contain the clean Job Description + Key Skills.
   - For Internshala, description intentionally contains ONLY the clean Skill(s) required section.
2. Extract candidate requirements, not every noun appearing on the page.
3. required_skills: technical or professional skills explicitly required,
   expected, used in core responsibilities, or listed in a real skills section.
4. preferred_skills: only skills clearly marked preferred, bonus, plus,
   nice-to-have, advantageous, or optional.
5. NEVER classify benefits/perks as skills. Examples to exclude:
   5 days a week, health/life insurance, informal dress code, free snacks,
   certificate, letter of recommendation, flexible work hours, job offer.
6. Do not classify company names/products or generic benefits as skills.
7. Keep concise canonical names where possible: React, JavaScript, Node.js,
   REST API, PostgreSQL, Git, etc.
8. If the JD explicitly lists multiple alternative technologies, preserve them;
   do not invent which one is mandatory.
9. Experience must be numeric years only when stated; otherwise null.
10. Education levels and degree fields must be separated.
11. Unknown fields are [] or null. Never guess.
12. extraction_confidence is extraction confidence, not candidate suitability.
13. Preserve input_id exactly so results map back to the correct job.

Return only the strict schema."""


def _clean_list(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    if not isinstance(values, list):
        return result

    for value in values:
        clean = " ".join(str(value or "").split()).strip(" ,;:-")
        if not clean:
            continue

        canonical = canonicalize_skill(clean)
        known = set(extract_known_skills(clean))

        normalized = (
            canonical
            if canonical in known or canonical != clean.casefold()
            else clean
        )

        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)

    return result


def _normalise_result(data: dict[str, Any], title: str) -> dict[str, Any]:
    confidence = data.get("extraction_confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "role_title": " ".join(
            str(data.get("role_title") or title or "").split()
        ),
        "required_skills": _clean_list(data.get("required_skills")),
        "preferred_skills": _clean_list(data.get("preferred_skills")),
        "min_years_experience": data.get("min_years_experience"),
        "max_years_experience": data.get("max_years_experience"),
        "education_requirements": _clean_list(
            data.get("education_requirements")
        ),
        "degree_fields": _clean_list(data.get("degree_fields")),
        "mandatory_requirements": _clean_list(
            data.get("mandatory_requirements")
        ),
        "preferred_requirements": _clean_list(
            data.get("preferred_requirements")
        ),
        "location_requirements": _clean_list(
            data.get("location_requirements")
        ),
        "work_authorization_requirements": _clean_list(
            data.get("work_authorization_requirements")
        ),
        "extraction_confidence": max(0.0, min(1.0, confidence)),
    }


def _extract_experience_locally(text: str) -> tuple[float | None, float | None]:
    lower = text.casefold()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*years?",
        lower,
    )
    if match:
        return float(match.group(1)), float(match.group(2))

    for pattern in (
        r"(\d+(?:\.\d+)?)\s*\+\s*years?",
        r"minimum\s+(\d+(?:\.\d+)?)\s*years?",
        r"at\s+least\s+(\d+(?:\.\d+)?)\s*years?",
    ):
        match = re.search(pattern, lower)
        if match:
            return float(match.group(1)), None

    if re.search(r"\bfresher\b|\b0\s*years?\b", lower):
        return 0.0, None

    return None, None


def _local_fallback(title: str, description: str) -> dict[str, Any]:
    description = description or ""
    chunks = re.split(r"(?<=[.!?])\s+|\n+", description)

    preferred_markers = (
        "preferred", "nice to have", "nice-to-have",
        "plus", "bonus", "advantage", "good to have",
    )

    preferred_text = "\n".join(
        chunk for chunk in chunks
        if any(marker in chunk.casefold() for marker in preferred_markers)
    )
    required_text = "\n".join(
        chunk for chunk in chunks
        if not any(marker in chunk.casefold() for marker in preferred_markers)
    )

    required = extract_known_skills(required_text)
    required_set = set(required)
    preferred = [
        skill for skill in extract_known_skills(preferred_text)
        if skill not in required_set
    ]

    min_exp, max_exp = _extract_experience_locally(description)
    lower = description.casefold()

    education: list[str] = []
    if re.search(r"\bb\.?\s*tech\b|\bbachelor'?s?\b|\bb\.?\s*e\.?\b", lower):
        education.append("Bachelor's degree")
    if re.search(r"\bm\.?\s*tech\b|\bmaster'?s?\b|\bm\.?\s*e\.?\b", lower):
        education.append("Master's degree")

    fields = [
        field for field in (
            "Computer Science", "Information Technology", "Engineering",
            "Data Science", "Statistics", "Mathematics",
        )
        if field.casefold() in lower
    ]

    return {
        "role_title": title or "",
        "required_skills": required,
        "preferred_skills": preferred,
        "min_years_experience": min_exp,
        "max_years_experience": max_exp,
        "education_requirements": education,
        "degree_fields": fields,
        "mandatory_requirements": [],
        "preferred_requirements": [],
        "location_requirements": [],
        "work_authorization_requirements": [],
        "extraction_confidence": 0.55 if (required or preferred) else 0.35,
        "_extraction_method": "local_fallback",
    }


async def _respect_batch_interval() -> None:
    global _last_request_started

    async with _rate_lock:
        now = time.monotonic()
        wait = (
            float(settings.GROQ_BATCH_MIN_INTERVAL_SECONDS)
            - (now - _last_request_started)
        )
        if wait > 0:
            await asyncio.sleep(wait)

        _last_request_started = time.monotonic()


def _bounded_job(job: dict[str, Any], input_id: int) -> dict[str, Any]:
    max_chars = max(1500, int(settings.GROQ_MAX_JOB_CHARS))
    return {
        "input_id": input_id,
        "source": str(job.get("source") or "").strip().lower(),
        "title": " ".join(str(job.get("title") or "").split()),
        "description": str(job.get("description") or "").strip()[:max_chars],
    }


async def _call_groq_batch(
    batch: Sequence[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    payload_jobs = [
        _bounded_job(job, index)
        for index, job in enumerate(batch)
    ]

    payload = {
        "model": settings.GROQ_REQUIREMENT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"jobs": payload_jobs},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "temperature": 0,
        "reasoning_effort": "low",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "career_job_requirements_batch",
                "strict": True,
                "schema": BATCH_SCHEMA,
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(4):
        await _respect_batch_interval()

        try:
            async with httpx.AsyncClient(timeout=75.0) as client:
                response = await client.post(
                    GROQ_URL,
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 429:
                retry_after = response.headers.get("retry-after")
                try:
                    delay = float(retry_after) if retry_after else 30.0
                except ValueError:
                    delay = 30.0

                logger.warning(
                    "Groq batch rate-limited; obeying retry-after %.1fs.",
                    delay,
                )
                await asyncio.sleep(max(1.0, min(delay, 90.0)))
                continue

            response.raise_for_status()
            body = response.json()
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )

            if not content:
                raise ValueError("Groq returned empty structured content.")

            parsed = json.loads(content)
            mapped: dict[int, dict[str, Any]] = {}

            for item in parsed.get("jobs", []):
                input_id = int(item["input_id"])
                if input_id < 0 or input_id >= len(batch):
                    continue

                title = str(batch[input_id].get("title") or "")
                result = _normalise_result(
                    item.get("requirements") or {},
                    title,
                )
                result["_extraction_method"] = "groq_batch_strict_json"
                mapped[input_id] = result

            return mapped

        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.warning(
                "Groq batch extraction attempt %d failed: %s",
                attempt + 1,
                exc,
            )
            if attempt < 3:
                await asyncio.sleep(min(2 ** (attempt + 1), 12))

    return {}


async def extract_job_requirements_batch(
    jobs: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Return one requirements dict per input job, preserving order.
    Never fails the scrape because local fallback is always available.
    """
    if not jobs:
        return []

    fallbacks = [
        _local_fallback(
            str(job.get("title") or ""),
            str(job.get("description") or ""),
        )
        for job in jobs
    ]

    if not settings.GROQ_API_KEY:
        logger.info(
            "GROQ_API_KEY not configured; using local extraction for %d jobs.",
            len(jobs),
        )
        return fallbacks

    batch_size = max(
        1,
        min(6, int(settings.GROQ_REQUIREMENT_BATCH_SIZE)),
    )

    results: list[dict[str, Any] | None] = [None] * len(jobs)

    for start in range(0, len(jobs), batch_size):
        chunk = jobs[start:start + batch_size]

        # Jobs with no meaningful text do not consume API quota.
        meaningful_positions = [
            i for i, job in enumerate(chunk)
            if len(str(job.get("description") or "").strip()) >= 40
        ]

        if not meaningful_positions:
            for i in range(len(chunk)):
                results[start + i] = fallbacks[start + i]
            continue

        meaningful_jobs = [chunk[i] for i in meaningful_positions]
        mapped = await _call_groq_batch(meaningful_jobs)

        for local_index, original_chunk_index in enumerate(meaningful_positions):
            global_index = start + original_chunk_index
            result = mapped.get(local_index)

            if result is None:
                result = fallbacks[global_index]

            results[global_index] = result

            logger.info(
                "Requirement extraction: %s | method=%s | required=%s | preferred=%s",
                jobs[global_index].get("title"),
                result.get("_extraction_method"),
                result.get("required_skills"),
                result.get("preferred_skills"),
            )

        for i in range(len(chunk)):
            global_index = start + i
            if results[global_index] is None:
                results[global_index] = fallbacks[global_index]

    return [result or fallbacks[i] for i, result in enumerate(results)]


async def extract_job_requirements(
    *,
    title: str,
    description: str,
) -> dict[str, Any]:
    """Backward-compatible one-job wrapper."""
    return (
        await extract_job_requirements_batch([
            {"title": title, "description": description}
        ])
    )[0]
