"""
CareerSync V4 local skill engine.

Goals
-----
- No LLM call for normal resume parsing.
- No semantic model needed for job scoring.
- Canonical aliases so React.js == React, NodeJS == Node.js, etc.
- Inference graph for umbrella capabilities such as Web Development / MERN.
- Unknown structured skills are preserved instead of discarded.
- Perks/benefits are rejected before they become job skills.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

# Canonical -> aliases. Keep this centralized so resume parsing, scraper cleanup
# and job matching all use the same vocabulary.
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    # Broad capabilities
    "web development": ("web development", "web developer", "web dev"),
    "frontend development": ("frontend development", "front-end development", "frontend developer", "front end developer"),
    "backend development": ("backend development", "back-end development", "backend developer", "back end developer"),
    "full stack development": ("full stack development", "full-stack development", "fullstack development", "full stack developer", "fullstack developer"),
    "mern stack": ("mern", "mern stack", "mern developer"),
    "mean stack": ("mean", "mean stack", "mean developer"),

    # Programming
    "c": ("c",),
    "c++": ("c++", "cpp"),
    "c#": ("c#", "c sharp"),
    "java": ("java",),
    "python": ("python",),
    "javascript": ("javascript", "java script", "js", "es6", "es6+"),
    "typescript": ("typescript", "type script", "ts"),
    "go": ("golang", "go language"),
    "rust": ("rust",),
    "ruby": ("ruby",),
    "php": ("php",),
    "kotlin": ("kotlin",),
    "swift": ("swift",),

    # Frontend
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    "react": ("react", "react.js", "reactjs"),
    "redux": ("redux", "redux toolkit"),
    "react hooks": ("react hooks", "hooks"),
    "react context api": ("react context api", "context api"),
    "tailwind css": ("tailwind", "tailwind css"),
    "bootstrap": ("bootstrap",),
    "material ui": ("material ui", "mui"),
    "angular": ("angular", "angularjs", "angular.js", "angular 2"),
    "vue.js": ("vue", "vue.js", "vuejs"),
    "next.js": ("next.js", "nextjs", "next js"),
    "vite": ("vite",),
    "jquery": ("jquery", "j query"),

    # Backend / APIs
    "node.js": ("node.js", "nodejs", "node js"),
    "express.js": ("express.js", "expressjs", "express js", "express"),
    "fastapi": ("fastapi", "fast api"),
    "flask": ("flask",),
    "django": ("django",),
    "spring boot": ("spring boot", "springboot"),
    "rest api": ("rest api", "rest apis", "restful api", "restful apis", "restful services"),
    "graphql": ("graphql",),
    "websocket": ("websocket", "websockets", "web socket"),
    "socket.io": ("socket.io", "socketio"),
    "microservices": ("microservices", "micro services", "microservice architecture"),
    "jwt": ("jwt", "json web token", "json web tokens"),
    "oauth": ("oauth", "oauth2", "oauth 2.0"),

    # DB
    "sql": ("sql",),
    "mysql": ("mysql",),
    "postgresql": ("postgresql", "postgres", "postgre sql"),
    "mongodb": ("mongodb", "mongo db"),
    "redis": ("redis",),
    "sqlite": ("sqlite",),
    "oracle": ("oracle",),
    "neon postgresql": ("neon postgresql", "neon db", "neon"),

    # DevOps / cloud
    "aws": ("aws", "amazon web services"),
    "azure": ("azure", "microsoft azure"),
    "gcp": ("gcp", "google cloud platform", "google cloud"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "git": ("git",),
    "github": ("github", "git hub"),
    "gitlab": ("gitlab",),
    "ci/cd": ("ci/cd", "cicd", "continuous integration", "continuous deployment"),
    "linux": ("linux",),

    # Testing / tooling
    "postman": ("postman",),
    "playwright": ("playwright",),
    "selenium": ("selenium",),
    "jest": ("jest",),
    "react testing library": ("react testing library", "rtl"),
    "celery": ("celery",),
    "judge0": ("judge0", "judge 0"),

    # AI / data
    "machine learning": ("machine learning", "ml"),
    "deep learning": ("deep learning",),
    "artificial intelligence": ("artificial intelligence", "ai"),
    "nlp": ("nlp", "natural language processing"),
    "computer vision": ("computer vision",),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "tensorflow": ("tensorflow", "tensor flow"),
    "pytorch": ("pytorch", "py torch"),
    "pandas": ("pandas", "panda"),
    "numpy": ("numpy", "num py"),
    "matplotlib": ("matplotlib",),
    "xgboost": ("xgboost", "xg boost"),
    "lightgbm": ("lightgbm", "light gbm"),
    "langchain": ("langchain", "lang chain"),
    "faiss": ("faiss",),
    "hugging face": ("hugging face", "huggingface"),
    "gemini": ("gemini", "google gemini"),
    "groq": ("groq", "chatgroq"),
    "openai": ("openai", "open ai", "openai api"),
    "llm": ("llm", "llms", "large language model", "large language models"),
    "rag": ("rag", "retrieval augmented generation", "retrieval-augmented generation"),
    "streamlit": ("streamlit",),

    # Mobile / misc
    "flutter": ("flutter",),
    "react native": ("react native",),
    "firebase": ("firebase",),

    # Business / analytics / professional
    "excel": ("excel", "microsoft excel", "ms excel"),
    "power bi": ("power bi", "powerbi"),
    "tableau": ("tableau",),
    "communication": ("communication", "communication skills"),
    "written communication": ("written communication",),
    "spoken english": ("spoken english", "english proficiency spoken"),
    "written english": ("written english", "english proficiency written"),
    "problem solving": ("problem solving", "problem-solving"),
    "team collaboration": ("team collaboration", "collaboration"),
    "project management": ("project management",),
    "agile": ("agile", "scrum"),
}

# Inference is deliberately conservative. No backend -> Python/Java inference.
SKILL_IMPLICATIONS: dict[str, dict[str, float]] = {
    "web development": {
        "html": 0.85,
        "css": 0.85,
        "javascript": 0.80,
    },
    "frontend development": {
        "html": 0.90,
        "css": 0.90,
        "javascript": 0.85,
    },
    "full stack development": {
        "html": 0.85,
        "css": 0.85,
        "javascript": 0.85,
    },
    "mern stack": {
        "mongodb": 0.95,
        "express.js": 0.95,
        "react": 0.95,
        "node.js": 0.95,
        "javascript": 0.90,
        "html": 0.80,
        "css": 0.80,
    },
    "mean stack": {
        "mongodb": 0.95,
        "express.js": 0.95,
        "angular": 0.95,
        "node.js": 0.95,
        "javascript": 0.90,
    },
    "react": {"javascript": 0.80},
    "node.js": {"javascript": 0.80},
    "next.js": {"react": 0.85, "javascript": 0.75},
    "express.js": {"node.js": 0.85},
}

NON_SKILL_EXACT = {
    "5 days a week",
    "informal dress code",
    "free snacks & beverages",
    "free snacks and beverages",
    "health insurance",
    "life insurance",
    "certificate",
    "letter of recommendation",
    "flexible work hours",
    "job offer",
    "cab/transport facility",
    "medical insurance",
    "number of openings",
}

NON_SKILL_PATTERNS = (
    r"\b\d+\s*days?\s+a\s+week\b",
    r"\binsurance\b",
    r"\bdress\s+code\b",
    r"\bsnacks?\b",
    r"\bbeverages?\b",
    r"\bcertificate\b",
    r"\bletter\s+of\s+recommendation\b",
    r"\bflexible\s+work\s+hours?\b",
    r"\bjob\s+offer\b",
    r"\btransport\b",
    r"\bcab\s+facility\b",
)

RESUME_SKILL_LINE_LABELS = (
    "technical skills",
    "skills",
    "programming languages",
    "languages",
    "frameworks",
    "frameworks/libraries",
    "libraries",
    "developer tools",
    "tools",
    "tools & technologies",
    "technologies",
    "databases",
    "cloud",
    "coursework",
)


def normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _contains_alias(text: str, alias: str) -> bool:
    text = str(text or "").casefold()
    alias = normalize_text(alias).casefold()
    if not alias:
        return False

    # Short ambiguous tokens need strict boundaries.
    pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def canonicalize_skill(value: str | None) -> str:
    clean = normalize_text(value).strip(" ,;:|•-").casefold()
    if not clean:
        return ""

    for canonical, aliases in SKILL_ALIASES.items():
        if clean == canonical:
            return canonical
        if any(clean == alias.casefold() for alias in aliases):
            return canonical

    # Preserve unknown structured skills instead of throwing them away.
    return clean


def is_non_skill(value: str | None) -> bool:
    clean = normalize_text(value).strip(" .,:;-")
    low = clean.casefold()

    if not clean or low in NON_SKILL_EXACT:
        return True
    if len(clean) > 100:
        return True
    return any(re.search(pattern, low) for pattern in NON_SKILL_PATTERNS)


def normalize_skill_list(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for raw in values or []:
        if is_non_skill(raw):
            continue
        skill = canonicalize_skill(raw)
        if not skill or skill in seen:
            continue
        seen.add(skill)
        result.append(skill)

    return result


def extract_dictionary_skills(text: str) -> list[str]:
    text = str(text or "")
    found: list[str] = []

    for canonical, aliases in SKILL_ALIASES.items():
        if any(_contains_alias(text, alias) for alias in aliases):
            found.append(canonical)

    return found


def _split_skill_candidates(value: str) -> list[str]:
    value = str(value or "")
    value = re.sub(r"[•●▪◦]", ",", value)
    value = value.replace(" / ", ",")
    parts = re.split(r"[,;|]", value)
    return [normalize_text(part).strip(" .:-") for part in parts if normalize_text(part)]


def extract_resume_section_skills(text: str) -> list[str]:
    """
    Capture arbitrary skills listed in structured resume lines, even if they
    are not yet in SKILL_ALIASES.

    Examples:
        Frameworks/Libraries: React.js, LangChain, Matplotlib
        Tools & Technologies: Python, FAISS, Streamlit
    """
    results: list[str] = []

    for raw_line in str(text or "").splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue

        low = line.casefold()

        # Labeled skill lines.
        matched_label = None
        for label in RESUME_SKILL_LINE_LABELS:
            if low.startswith(label.casefold() + ":"):
                matched_label = label
                break

        if matched_label:
            value = line.split(":", 1)[1]
            results.extend(_split_skill_candidates(value))
            continue

        # Project technology lines.
        if "tools & technologies:" in low or "technologies:" in low:
            value = line.split(":", 1)[1] if ":" in line else ""
            results.extend(_split_skill_candidates(value))

    # Reject obvious sentence-like fragments.
    cleaned: list[str] = []
    for candidate in results:
        if not candidate or is_non_skill(candidate):
            continue
        if len(candidate) > 55:
            continue
        if len(candidate.split()) > 6:
            continue
        cleaned.append(candidate)

    return normalize_skill_list(cleaned)


def extract_explicit_resume_skills(text: str) -> list[str]:
    skills = extract_dictionary_skills(text)
    skills.extend(extract_resume_section_skills(text))
    return normalize_skill_list(skills)


def expand_skill_profile(
    explicit_skills: Sequence[str] | None,
) -> dict[str, float]:
    """
    Return canonical skill -> confidence.
    Explicit = 1.0. Inferred skills receive partial confidence.
    """
    expanded = {
        skill: 1.0
        for skill in normalize_skill_list(explicit_skills)
    }

    for _ in range(4):
        changed = False
        for source, source_conf in list(expanded.items()):
            for target, edge_conf in SKILL_IMPLICATIONS.get(source, {}).items():
                confidence = source_conf * edge_conf
                if confidence > expanded.get(target, 0.0):
                    expanded[target] = confidence
                    changed = True
        if not changed:
            break

    return expanded


def extract_resume_skill_profile(text: str) -> dict:
    explicit = extract_explicit_resume_skills(text)
    expanded = expand_skill_profile(explicit)
    inferred = {
        skill: round(confidence, 2)
        for skill, confidence in expanded.items()
        if skill not in set(explicit)
    }

    return {
        "explicit": explicit,
        "inferred": inferred,
        "all_skills": list(expanded.keys()),
        "confidence_map": expanded,
    }


def extract_key_skills_from_description(description: str | None) -> list[str]:
    """
    Backward compatibility for rows/scrapers that still store:
        Required / Key Skills:
        React, Node.js, ...
    """
    text = str(description or "")
    match = re.search(
        r"Required\s*/?\s*Key\s*Skills\s*:\s*(.+?)(?:\n\s*\n|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    raw = match.group(1)
    return normalize_skill_list(_split_skill_candidates(raw))


def direct_skill_match(
    *,
    required_skills: Sequence[str] | None,
    preferred_skills: Sequence[str] | None,
    resume_text: str,
    saved_user_skills: Sequence[str] | None,
) -> dict:
    """
    Direct skill-to-skill comparison.

    Explicit match = 100% credit.
    Inferred match = implication confidence, e.g. Web Development -> HTML 85%.
    """
    explicit = set(extract_explicit_resume_skills(resume_text))
    expanded = expand_skill_profile(explicit)

    # Manual/profile skills can add capabilities. Skills already inferred from
    # resume are NOT promoted to explicit just because all skills were saved.
    for skill in normalize_skill_list(saved_user_skills):
        if skill not in expanded:
            expanded[skill] = 1.0
            explicit.add(skill)

    required = normalize_skill_list(required_skills)
    preferred = normalize_skill_list(preferred_skills)

    def coverage(job_skills: list[str]) -> tuple[float | None, list[str], list[dict], list[str]]:
        if not job_skills:
            return None, [], [], []

        total = 0.0
        matched_explicit: list[str] = []
        matched_inferred: list[dict] = []
        missing: list[str] = []

        for skill in job_skills:
            confidence = float(expanded.get(skill, 0.0))
            total += confidence

            if confidence >= 0.999:
                matched_explicit.append(skill)
            elif confidence > 0:
                matched_inferred.append({
                    "skill": skill,
                    "confidence": round(confidence, 2),
                })
            else:
                missing.append(skill)

        return total / len(job_skills), matched_explicit, matched_inferred, missing

    req_score, req_explicit, req_inferred, req_missing = coverage(required)
    pref_score, pref_explicit, pref_inferred, pref_missing = coverage(preferred)

    return {
        "required_coverage": req_score,
        "preferred_coverage": pref_score,
        "required_skills": required,
        "preferred_skills": preferred,
        "matched_required_skills": req_explicit,
        "inferred_required_skills": req_inferred,
        "missing_required_skills": req_missing,
        "matched_preferred_skills": pref_explicit,
        "inferred_preferred_skills": pref_inferred,
        "missing_preferred_skills": pref_missing,
        "explicit_candidate_skills": sorted(explicit),
        "expanded_candidate_skills": {
            skill: round(conf, 2)
            for skill, conf in sorted(expanded.items())
        },
    }
