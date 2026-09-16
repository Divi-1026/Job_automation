"""
Naukri JD -> CORE technical skill extractor.

The LLM is used ONLY for extraction.
It never calculates confidence and never sees the candidate resume.

Input:
    title + clean Naukri JD only

Excluded from model input:
    - skill_query
    - normal Naukri Key Skills
    - candidate profile/resume

Output:
    evidence-validated list of core technical skills from the actual JD.

If Groq is unavailable/rate-limited, a local dictionary fallback is used so
scraping and DB saving continue.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

from app.core.config import settings
from app.utils.semantic_match import extract_known_skills, canonicalize_skill


logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """
You are a strict technical-skill extraction engine for software job descriptions.

Your ONLY task is to extract a COMPLETE, EXHAUSTIVE list of explicitly stated
technical skills from each supplied ACTUAL JOB DESCRIPTION.

CRITICAL GOAL:
Do not miss technical skills that are explicitly written in the JD. Read the
ENTIRE JD, including responsibilities, Job Requirements, Minimum
Qualifications, Mandatory, Required, Must Have, qualifications, and technical
experience statements.

INCLUDE when explicitly present:
- programming languages
- frameworks and libraries
- runtimes and platforms
- databases, data stores, caches and search engines
- cloud providers and named cloud services
- APIs and API styles
- protocols and data formats
- version-control tools
- testing tools/frameworks
- messaging/event-streaming technologies
- containers and orchestration
- CI/CD, DevOps and Infrastructure-as-Code technologies
- frontend/backend technologies
- named architecture/engineering technologies when they are technical
  requirements, e.g. microservices, event-driven architecture, CQRS,
  WebSockets, distributed systems
- technical domain platforms only when explicitly required by the JD

EXCLUDE:
- soft skills: communication, collaboration, problem solving, leadership
- generic verbs: develop, manage, coordinate, troubleshoot, design
- generic role names: developer, engineer, frontend developer, backend developer
- company/industry names
- education/degree names
- locations, salary, years of experience
- generic prose such as "coding", "software development", "computer science"
  unless it is a specific technology/tool
- skills that occur ONLY in Preferred Qualifications, Good to Have,
  Nice to Have, Bonus, Advantage, or optional/preferred sections
- anything not explicitly present in the supplied JD

MANDATORY RULES:
1. Inspect every sentence of the JD before answering.
2. Mandatory/Required/Must-have/Minimum Qualifications have highest priority.
3. Responsibilities may contain required technical stack; include explicit
   technologies from them too.
4. Never infer a skill from the job title.
5. Never infer a technology from another technology.
6. Never convert plain "Express" into "Express.js".
7. If the JD explicitly says Node.JS and Express.JS, BOTH must be returned.
8. If the JD says "MongoDB or PostgreSQL", return BOTH because both are
   explicitly stated acceptable technical requirements.
9. Preserve distinct technologies: Node.js != Express.js, Java != JavaScript,
   Angular != AngularJS, SQL != PostgreSQL.
10. Do not return a partial shortlist. Return ALL qualifying technical skills.
11. Every returned skill must have direct textual evidence in the supplied JD.
12. Before finalizing, perform a second pass over the JD and check that no
    explicit technical skill from mandatory/required/minimum/responsibility
    sections was omitted.
13. Output JSON only. No explanation, markdown, confidence score, or prose.

For each input job return:
{
  "input_id": <integer>,
  "core_skills": ["skill 1", "skill 2", "..."]
}

Top-level format:
{
  "jobs": [
    {"input_id": 0, "core_skills": ["..."]}
  ]
}

If no qualifying technical skill is explicitly present, return an empty list.
"""




def _setting_or_env(name: str, default=None):
    """
    Resolve config robustly.

    Some CareerSync config classes do not declare every Groq field, while the
    value still exists in server/.env. Reading both prevents silent fallback.
    """
    value = getattr(settings, name, None)
    if value not in (None, ""):
        return value

    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value

    return default


def _parse_json_object(content: str) -> dict:
    if not content:
        raise ValueError("Empty Groq response")

    text = content.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s*```$", "", text)

    # First try direct JSON parsing
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Extract first balanced JSON object
    start = text.find("{")

    if start == -1:
        raise ValueError(
            f"No JSON object found in Groq response: {text[:500]}"
        )

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\" and in_string:
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1

        elif ch == "}":
            depth -= 1

            if depth == 0:
                candidate = text[start : i + 1]

                try:
                    parsed = json.loads(candidate)

                    if isinstance(parsed, dict):
                        return parsed

                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON returned by Groq: {exc}; "
                        f"response={text[:500]}"
                    ) from exc

    raise ValueError(
        f"Incomplete JSON object from Groq: {text[:500]}"
    )


def _clean_skill_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    seen = set()
    result = []

    for raw in values:
        value = " ".join(str(raw or "").split()).strip(" ,;:-")
        if not value or len(value) > 80 or len(value.split()) > 7:
            continue

        if value.casefold() == "express":
            continue

        canonical = canonicalize_skill(value)
        key = canonical.casefold()
        if not key or key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result



def _norm_for_evidence(text: str) -> str:
    text = str(text or "").casefold()
    text = text.replace("c++", "cplusplus").replace("c#", "csharp")
    text = re.sub(r"[^a-z0-9.+#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_EVIDENCE_ALIASES = {
    "react.js": ("react.js", "reactjs", "react js"),
    "node.js": ("node.js", "nodejs", "node js"),
    "express.js": ("express.js", "expressjs", "express js"),
    "next.js": ("next.js", "nextjs", "next js"),
    "vue.js": ("vue.js", "vuejs", "vue js"),
    "rest api": ("rest api", "restful api", "restful apis", "rest apis"),
    "postgresql": ("postgresql", "postgres"),
    "mongodb": ("mongodb", "mongo db"),
    "mysql": ("mysql",),
    "ms sql server": ("ms sql server", "mssql", "sql server"),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    "tailwind css": ("tailwind css", "tailwind"),
    "bootstrap": ("bootstrap",),
    "angular": ("angular",),
    "angularjs": ("angularjs", "angular.js"),
    "jquery": ("jquery",),
    "java": ("java",),
    "python": ("python",),
    "php": ("php",),
    "ruby": ("ruby",),
    "sql": ("sql",),
    "redis": ("redis",),
    "graphql": ("graphql",),
    "json": ("json",),
    "xml": ("xml",),
    "git": ("git",),
    "github": ("github",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud platform", "google cloud"),
    "junit": ("junit",),
    "pytest": ("pytest",),
    "selenium": ("selenium",),
    "elasticsearch": ("elasticsearch", "elastic search"),
    "ajax": ("ajax",),
    "http": ("http", "https"),
    "asp.net": ("asp.net", "asp net"),
    "blazor": ("blazor",),
    "c#": ("c#", "csharp"),
    "c++": ("c++", "cplusplus"),
    "spring boot": ("spring boot", "springboot"),
    "fastapi": ("fastapi", "fast api"),
    "django": ("django",),
    "flask": ("flask",),
    "socket.io": ("socket.io", "socketio", "socket io"),
    "ci/cd": ("ci/cd", "ci cd", "continuous integration", "continuous deployment"),
}



_LOCAL_TECH_PHRASES = {
    "node.js": ("node.js", "nodejs", "node js"),
    "express.js": ("express.js", "expressjs", "express js"),
    "nestjs": ("nestjs", "nest.js", "nest js"),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "react.js": ("react.js", "reactjs", "react js"),
    "next.js": ("next.js", "nextjs", "next js"),
    "vue.js": ("vue.js", "vuejs", "vue js"),
    "angular": ("angular",),
    "angularjs": ("angularjs", "angular.js"),
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    "tailwind css": ("tailwind css", "tailwind"),
    "bootstrap": ("bootstrap",),
    "jquery": ("jquery",),
    "python": ("python",),
    "java": ("java",),
    "c++": ("c++",),
    "c#": ("c#",),
    "php": ("php",),
    "ruby": ("ruby",),
    "go": ("golang", "go language"),
    "rust": ("rust",),
    "sql": ("sql",),
    "mysql": ("mysql",),
    "postgresql": ("postgresql", "postgres"),
    "mongodb": ("mongodb", "mongo db"),
    "ms sql server": ("ms sql server", "mssql", "sql server"),
    "redis": ("redis",),
    "elasticsearch": ("elasticsearch", "elastic search"),
    "rest api": ("rest api", "rest apis", "restful api", "restful apis"),
    "graphql": ("graphql",),
    "websockets": ("websocket", "websockets"),
    "http": ("http", "https"),
    "json": ("json",),
    "xml": ("xml",),
    "git": ("git",),
    "github": ("github",),
    "gitlab": ("gitlab",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"),
    "aws ecs": ("ecs", "amazon ecs"),
    "aws eks": ("eks", "amazon eks"),
    "aws lambda": ("lambda", "aws lambda"),
    "aws rds": ("rds", "amazon rds"),
    "amazon s3": ("s3", "amazon s3"),
    "amazon cloudwatch": ("cloudwatch",),
    "aws api gateway": ("api gateway",),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud platform", "google cloud"),
    "kafka": ("kafka", "apache kafka"),
    "rabbitmq": ("rabbitmq", "rabbit mq"),
    "microservices": ("microservices", "microservice architecture", "microservice"),
    "event-driven architecture": ("event-driven architecture", "event driven architecture", "event-driven"),
    "distributed systems": ("distributed systems", "distributed system"),
    "cqrs": ("cqrs",),
    "ci/cd": ("ci/cd", "ci cd", "continuous integration", "continuous deployment"),
    "infrastructure as code": ("infrastructure as code", "iac"),
    "terraform": ("terraform",),
    "junit": ("junit",),
    "pytest": ("pytest",),
    "selenium": ("selenium",),
    "spring boot": ("spring boot", "springboot"),
    "django": ("django",),
    "flask": ("flask",),
    "fastapi": ("fastapi", "fast api"),
    "socket.io": ("socket.io", "socketio", "socket io"),
    "asp.net": ("asp.net", "asp net"),
    "blazor": ("blazor",),
    "ajax": ("ajax",),
}


def _strip_preferred_sections(text: str) -> str:
    """
    Remove optional/preferred sections before deterministic exact extraction.
    The original clean JD is preserved elsewhere for semantic embedding.
    """
    value = str(text or "")
    return re.sub(
        r"(?is)"
        r"(?:^|\n)\s*(?:preferred qualifications?|preferred skills?|"
        r"good\s+to\s+have|nice\s+to\s+have|bonus|advantages?)\s*:?\s*"
        r".*?"
        r"(?=(?:\n\s*(?:mandatory|job requirements?|requirements?|"
        r"minimum qualifications?|must\s+have|required|responsibilities|"
        r"education|role|key skills)\b)|\Z)",
        "\n",
        value,
    )


def _local_exhaustive_skills(jd: str) -> list[str]:
    """
    Deterministic second extractor.

    It scans the actual JD (with preferred/optional blocks removed) for a
    curated technical vocabulary. It does NOT read skill_query or Naukri
    platform tags.
    """
    source = _strip_preferred_sections(jd)
    norm = _norm_for_evidence(source)

    found = []
    for canonical, aliases in _LOCAL_TECH_PHRASES.items():
        for alias in aliases:
            phrase = _norm_for_evidence(alias)
            if not phrase:
                continue
            if re.search(
                rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
                norm,
            ):
                found.append(canonical)
                break

    return found


def _skill_has_jd_evidence(skill: str, jd: str) -> bool:
    """
    Trust gate: accept an extracted skill only when the actual clean JD
    explicitly contains that skill or a controlled alias.
    """
    canonical = canonicalize_skill(skill)
    if not canonical or not jd:
        return False

    text = _norm_for_evidence(jd)
    aliases = _EVIDENCE_ALIASES.get(canonical)

    if aliases:
        for alias in aliases:
            phrase = _norm_for_evidence(alias)
            if phrase and re.search(
                rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
                text,
            ):
                return True
        return False

    phrase = _norm_for_evidence(skill)
    if len(phrase) < 2:
        return False

    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
            text,
        )
    )


def _evidence_validate_skills(skills: list[str], jd: str) -> list[str]:
    accepted = []
    rejected = []

    for skill in _clean_skill_list(skills):
        if _skill_has_jd_evidence(skill, jd):
            accepted.append(skill)
        else:
            rejected.append(skill)

    if rejected:
        logger.warning(
            "[Naukri LLM] Rejected skills without JD evidence | %s",
            rejected,
        )

    return accepted


def _local_core_skills(title: str, jd: str) -> list[str]:
    """
    Deterministic fallback when Groq is unavailable.

    Priority:
      1. Mandatory / Required / Must-have portions of the clean JD
      2. Otherwise the clean JD excluding Preferred / Good-to-have blocks

    Platform Key Skills and skill_query are never used here.
    """
    text = str(jd or "")
    if not text.strip():
        return []

    mandatory_parts = []

    patterns = [
        r"(?is)\bmandatory\s*:?(.*?)(?=\n\s*(?:preferred|good\s+to\s+have|nice\s+to\s+have|education|role|key\s+skills)\b|\Z)",
        r"(?is)\bmust\s+have\s*:?(.*?)(?=\n\s*(?:preferred|good\s+to\s+have|nice\s+to\s+have|education|role|key\s+skills)\b|\Z)",
        r"(?is)\brequired(?:\s+skills?|\s+qualifications?)?\s*:?(.*?)(?=\n\s*(?:preferred|good\s+to\s+have|nice\s+to\s+have|education|role|key\s+skills)\b|\Z)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            chunk = (match.group(1) or "").strip()
            if chunk:
                mandatory_parts.append(chunk)

    if mandatory_parts:
        source = "\n".join(mandatory_parts)
    else:
        source = re.sub(
            r"(?is)\b(?:preferred|good\s+to\s+have|nice\s+to\s+have)\b.*?"
            r"(?=(?:\n\s*(?:mandatory|required|must\s+have|responsibilities|role|education|key\s+skills)\b)|\Z)",
            " ",
            text,
        )

    skills = extract_known_skills(source)

    # Plain "Express" is never Express.js.
    if not re.search(r"(?i)\bexpress(?:\.?\s*js)\b", source):
        skills = [x for x in skills if x != "express.js"]

    return skills


async def _groq_batch(batch: list[dict]) -> dict[int, list[str]] | None:
    api_key = _setting_or_env("GROQ_API_KEY")
    if not api_key:
        logger.warning(
            "[Naukri LLM] GROQ_API_KEY not available to worker; using local fallback."
        )
        return None

    model = str(
        _setting_or_env("GROQ_REQUIREMENT_MODEL", "openai/gpt-oss-120b")
    )
    max_chars = int(_setting_or_env("GROQ_MAX_JOB_CHARS", 7000) or 7000)

    payload_jobs = []
    for index, job in enumerate(batch):
        payload_jobs.append(
            {
                "input_id": index,
                "title": str(job.get("title") or "")[:300],
                # ONLY actual clean JD is sent to Groq.
                "description": str(job.get("_clean_jd") or "")[:max_chars],
            }
        )

    body = {
       "model": model,
       "temperature": 0,
       "reasoning_effort": "low",
       "include_reasoning": False,

       "messages": [
           {
              "role": "user",
              "content": (
                  SYSTEM_PROMPT
                  + "\n\nINPUT JOBS:\n"
                  + json.dumps(
                      {"jobs": payload_jobs},
                      ensure_ascii=False,
                  )
               ),
           },
       ],

    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = None

    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=75.0) as client:
                response = await client.post(GROQ_URL, headers=headers, json=body)

            if response.status_code == 429:
                retry_after = response.headers.get("retry-after")
                wait = 4.0 * attempt
                if retry_after:
                    try:
                        wait = min(float(retry_after), 30.0)
                    except Exception:
                        pass

                logger.warning(
                    "[Naukri LLM] rate-limited | attempt=%d/3 | wait=%.1fs",
                    attempt,
                    wait,
                )
                await asyncio.sleep(wait)
                continue

            if response.status_code >= 400:
                # Do not print response body because providers sometimes echo
                # request metadata. Status is enough for debugging.
                logger.warning(
                    "[Naukri LLM] Groq HTTP %s | model=%s | attempt=%d/3 | error=%s",
                    response.status_code,
                    model,
                    attempt,
                    response.text[:1000],
                )
                if response.status_code in {400, 401, 403, 404}:
                    return None
                await asyncio.sleep(2.0 * attempt)
                continue

            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""

            logger.info(
                "[Naukri LLM] Raw response preview | %s",
                content[:1000],
            )

            parsed = _parse_json_object(content)

            result = {}
            for item in parsed.get("jobs", []):
                try:
                    input_id = int(item.get("input_id"))
                except Exception:
                    continue

                result[input_id] = _clean_skill_list(item.get("core_skills"))

            logger.info(
                "[Naukri LLM] Groq batch success | model=%s | jobs=%d",
                model,
                len(batch),
            )
            return result

        except Exception as exc:
            last_error = exc
            logger.warning(
                "[Naukri LLM] Groq attempt failed | attempt=%d/3 | %s | error=%s",
                attempt,
                type(exc).__name__,
                str(exc),
            )

            if attempt < 3:
                await asyncio.sleep(2.0 * attempt)

    logger.warning(
        "[Naukri LLM] Groq unavailable after retries; using local fallback | %s",
        type(last_error).__name__ if last_error else "unknown",
    )
    return None


async def extract_naukri_core_skills_batch(jobs: list[dict]) -> list[list[str]]:
    """
    Returns one skill list per input job, preserving input order.

    Batched to reduce API calls. Missing/failed model outputs fall back locally.
    """
    if not jobs:
        return []

    batch_size = int(_setting_or_env("GROQ_REQUIREMENT_BATCH_SIZE", 5) or 5)
    batch_size = max(1, min(batch_size, 8))
    results: list[list[str]] = [[] for _ in jobs]

    for start in range(0, len(jobs), batch_size):
        batch = jobs[start : start + batch_size]
        model_result = await _groq_batch(batch)

        for local_index, job in enumerate(batch):
            jd_text = str(job.get("_clean_jd") or "")
            title_text = str(job.get("title") or "")

            # 1) Deterministic JD extraction always runs.
            #    This prevents a partial LLM response from silently dropping
            #    explicit mandatory skills such as Node.js / Express.js.
            local_primary = _local_core_skills(title_text, jd_text)
            local_exhaustive = _local_exhaustive_skills(jd_text)

            local_skills = []
            local_seen = set()
            for skill in [*local_primary, *local_exhaustive]:
                canonical = canonicalize_skill(skill)
                if not canonical or canonical in local_seen:
                    continue
                local_seen.add(canonical)
                local_skills.append(skill)

            local_skills = _evidence_validate_skills(local_skills, jd_text)

            # 2) Groq extraction is optional additional coverage, but every
            #    returned skill must still be evidenced in the SAME JD.
            groq_skills = []
            if model_result is not None:
                raw_model_skills = model_result.get(local_index) or []
                groq_skills = _evidence_validate_skills(raw_model_skills, jd_text)

            # 3) Union the two evidence-validated sources.
            #    LLM is never allowed to remove a deterministic JD skill.
            merged = []
            seen = set()
            for skill in [*local_skills, *groq_skills]:
                canonical = canonicalize_skill(skill)
                if not canonical or canonical in seen:
                    continue
                seen.add(canonical)
                merged.append(skill)

            skills = merged

            if groq_skills and local_skills:
                method = "groq_plus_local_evidence_validated"
            elif groq_skills:
                method = "groq_evidence_validated"
            else:
                method = "local_fallback"

            results[start + local_index] = skills

            logger.info(
                "[Naukri Skill Extraction] %s | method=%s | local=%s | groq=%s | final=%s",
                job.get("title"),
                method,
                local_skills,
                groq_skills,
                skills,
            )

        # Small gap between batches. Existing project config may choose a
        # larger interval; this keeps the scraper responsive.
        if start + batch_size < len(jobs):
            await asyncio.sleep(1.0)

    return results
