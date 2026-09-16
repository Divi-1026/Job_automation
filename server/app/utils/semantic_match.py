"""
CareerSync trustworthy hybrid matching.

Exact skill coverage is deterministic.

Naukri:
    Exact Required Skills =
        star-marked preferred Naukri keyskills
        UNION
        LLM-extracted core skills from clean JD

    Normal unstarred Naukri Key Skills are NOT exact skills.
    They only influence semantic embedding because they remain in description.

Internshala:
    Exact Required Skills =
        Internshala Skill(s) required

Final score:
    45% exact skill coverage
    30% calibrated semantic similarity
    15% resume evidence
    10% role alignment

This is a relevance score, not hiring probability.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = SentenceTransformer(MODEL_NAME)


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "c": ("c language",),
    "c++": ("c++", "cpp"),
    "c#": ("c#", "c sharp"),
    "java": ("java",),
    "python": ("python",),
    "javascript": ("javascript", "java script", "js", "es6", "es6+"),
    "typescript": ("typescript", "type script", "ts"),
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    "react.js": ("react.js", "reactjs", "react js", "react"),
    "redux": ("redux", "redux toolkit"),
    "tailwind css": ("tailwind css", "tailwind"),
    "bootstrap": ("bootstrap",),
    "jquery": ("jquery", "j query"),
    "angular": ("angular",),
    "angularjs": ("angularjs", "angular.js"),
    "vue.js": ("vue.js", "vuejs", "vue"),
    "next.js": ("next.js", "nextjs", "next js"),
    "react native": ("react native",),
    "node.js": ("node.js", "nodejs", "node js"),
    "express.js": ("express.js", "expressjs", "express js"),
    "fastapi": ("fastapi", "fast api"),
    "flask": ("flask",),
    "django": ("django",),
    "spring boot": ("spring boot", "springboot"),
    "blazor": ("blazor", "blazor pages"),
    "asp.net": ("asp.net", "asp net", "dotnet asp"),
    ".net": (".net", "dotnet"),
    "rest api": ("rest api", "rest apis", "restful api", "restful apis", "restful services"),
    "graphql": ("graphql", "graph ql"),
    "ajax": ("ajax",),
    "http": ("http", "https"),
    "json": ("json", "jsons"),
    "xml": ("xml", "xmls"),
    "sql": ("sql",),
    "ms sql server": ("ms sql server", "mssql", "sql server"),
    "mysql": ("mysql", "my sql"),
    "postgresql": ("postgresql", "postgres", "postgre sql"),
    "mongodb": ("mongodb", "mongo db"),
    "redis": ("redis",),
    "sqlite": ("sqlite",),
    "oracle": ("oracle",),
    "elasticsearch": ("elasticsearch", "elastic search"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure", "microsoft azure"),
    "gcp": ("gcp", "google cloud", "google cloud platform"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "git": ("git",),
    "github": ("github", "git hub"),
    "gitlab": ("gitlab",),
    "ci/cd": ("ci/cd", "cicd", "continuous integration", "continuous deployment"),
    "linux": ("linux",),
    "junit": ("junit",),
    "pyunit": ("pyunit",),
    "pytest": ("pytest",),
    "selenium": ("selenium",),
    "playwright": ("playwright",),
    "postman": ("postman",),
    "machine learning": ("machine learning",),
    "deep learning": ("deep learning",),
    "artificial intelligence": ("artificial intelligence",),
    "nlp": ("natural language processing", "nlp"),
    "scikit-learn": ("scikit-learn", "sklearn", "scikit learn"),
    "tensorflow": ("tensorflow",),
    "pytorch": ("pytorch",),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "langchain": ("langchain", "lang chain"),
    "faiss": ("faiss",),
    "streamlit": ("streamlit",),
    "firebase": ("firebase",),
    "php": ("php",),
    "laravel": ("laravel",),
    "ruby": ("ruby",),
    "go": ("golang", "go language"),
}


_GENERIC_NOT_EXACT = {
    "web application",
    "web application development",
    "web development",
    "frontend",
    "front end",
    "frontend developer",
    "backend",
    "back end",
    "backend developer",
    "software development",
    "software developer",
    "programming",
    "programming languages",
    "coding",
    "coding standards",
    "architecture",
    "workflow",
    "workflow analysis",
    "native",
    "communication",
    "teamwork",
    "problem solving",
}


def normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _contains_alias(text: str, alias: str) -> bool:
    text = str(text or "").casefold()
    alias = normalize_text(alias).casefold()
    if not alias:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def canonicalize_skill(value: str | None) -> str:
    clean = normalize_text(value).strip(" ,;:|•-").casefold()
    if not clean:
        return ""

    # Plain "express" is intentionally NOT Express.js.
    if clean == "express":
        return "express"

    for canonical, aliases in SKILL_ALIASES.items():
        if clean == canonical.casefold():
            return canonical
        if any(clean == alias.casefold() for alias in aliases):
            return canonical

    return clean


def extract_known_skills(text: str) -> list[str]:
    text = str(text or "")
    result = []

    for canonical, aliases in SKILL_ALIASES.items():
        if any(_contains_alias(text, alias) for alias in aliases):
            result.append(canonical)

    return result


def _dedupe_skills(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for raw in values:
        canonical = canonicalize_skill(raw)
        if not canonical or canonical in _GENERIC_NOT_EXACT or canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)
    return result


def create_embedding(text: str) -> list[float]:
    text = normalize_text(text)
    if not text:
        return []

    vector = _model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vector.astype(float).tolist()


def cosine_similarity_score(
    vector_a: Sequence[float] | None,
    vector_b: Sequence[float] | None,
) -> float:
    if not vector_a or not vector_b:
        return 0.0

    a = np.asarray(vector_a, dtype=float)
    b = np.asarray(vector_b, dtype=float)

    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape:
        return 0.0

    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0

    return max(0.0, min(1.0, float(np.dot(a, b) / (na * nb))))


def _calibrate_semantic(raw: float) -> float:
    """
    MiniLM cosine is not a probability.

    0.18 and below -> effectively unrelated
    0.78 and above -> extremely strong semantic relation
    """
    raw = max(0.0, min(1.0, raw))
    low, high = 0.18, 0.78
    return max(0.0, min(1.0, (raw - low) / (high - low)))


def _extract_exact_required_skills(job_text: str) -> list[str]:
    text = str(job_text or "")

    # New final architecture.
    match = re.search(
        r"(?is)\bExact\s+Required\s+Skills\s*:\s*(.+?)"
        r"(?=\n\s*(?:Preferred\s+Key\s+Skills|JD\s+Extracted\s+Skills|"
        r"Platform\s+Key\s+Skills|Internshala\s+Required\s+Skills|"
        r"Required\s+Experience|Eligibility|Education)\s*:|\Z)",
        text,
    )

    # Compatibility with older already-saved rows.
    if not match:
        match = re.search(
            r"(?is)\bRequired\s*/\s*Key\s*Skills\s*:\s*(.+?)"
            r"(?=\n\s*(?:Required\s+Experience|Eligibility|Education)\s*:|\Z)",
            text,
        )

    if not match:
        return []

    section = match.group(1)
    candidates = re.split(r"[,;\n|•]+", section)
    return _dedupe_skills(candidates)


def _resume_has_skill(
    resume_text: str,
    profile_skills: Sequence[str] | None,
    required_skill: str,
) -> tuple[bool, bool]:
    """
    Returns:
        matched_anywhere, evidenced_in_resume_text
    """
    required = canonicalize_skill(required_skill)
    if not required:
        return False, False

    profile = set(_dedupe_skills(profile_skills or []))
    resume_known = set(extract_known_skills(resume_text))

    if required in resume_known:
        return True, True

    if required in profile:
        # Check whether the same canonical skill is also actually evidenced
        # somewhere in resume text.
        evidenced = False
        aliases = SKILL_ALIASES.get(required, (required,))
        if any(_contains_alias(resume_text, alias) for alias in aliases):
            evidenced = True
        return True, evidenced

    aliases = SKILL_ALIASES.get(required, (required,))
    evidenced = any(_contains_alias(resume_text, alias) for alias in aliases)

    return evidenced, evidenced


def _skill_components(
    resume_text: str,
    profile_skills: Sequence[str] | None,
    job_text: str,
) -> tuple[float, float, list[str], list[str], list[str]]:
    required = _extract_exact_required_skills(job_text)

    if not required:
        # Neutral when the platform/JD exposes no trustworthy exact-skill set.
        return 0.5, 0.5, [], [], []

    matched = []
    missing = []
    evidenced_count = 0

    for skill in required:
        matched_any, evidenced = _resume_has_skill(
            resume_text,
            profile_skills,
            skill,
        )

        if matched_any:
            matched.append(skill)
        else:
            missing.append(skill)

        if evidenced:
            evidenced_count += 1

    coverage = len(matched) / len(required)
    evidence = evidenced_count / len(required)

    return coverage, evidence, required, matched, missing


def _extract_title(job_text: str) -> str:
    match = re.search(r"(?im)^\s*Job\s*title\s*:\s*(.+?)\s*$", job_text or "")
    return normalize_text(match.group(1)) if match else ""


def _role_alignment(resume_text: str, job_text: str) -> float:
    title = _extract_title(job_text)
    if not title:
        return 0.5

    t = title.casefold()
    r = str(resume_text or "").casefold()

    families = {
        "frontend": (
            ("frontend", "front end", "react", "angular", "vue"),
            ("react", "javascript", "typescript", "html", "css", "redux", "frontend"),
        ),
        "backend": (
            ("backend", "back end"),
            ("node", "express", "fastapi", "django", "flask", "spring", "rest api", "sql", "backend"),
        ),
        "fullstack": (
            ("full stack", "fullstack", "mern"),
            ("react", "node", "express", "mongodb", "full stack", "mern"),
        ),
        "data": (
            ("data scientist", "data analyst", "machine learning", "analytics"),
            ("python", "pandas", "numpy", "machine learning", "sql", "data science"),
        ),
        "devops": (
            ("devops", "cloud engineer"),
            ("docker", "kubernetes", "aws", "azure", "gcp", "ci/cd"),
        ),
    }

    detected = []
    for title_markers, resume_markers in families.values():
        if any(marker in t for marker in title_markers):
            score = sum(1 for marker in resume_markers if marker in r) / len(resume_markers)
            detected.append(min(1.0, 0.35 + score))

    if detected:
        return max(detected)

    # Unknown role family -> neutral, not punitive.
    return 0.5


def calculate_match_details(
    resume_embedding: list[float] | None,
    job_embedding: list[float] | None,
    user_skills: list[str] | None = None,
    job_text: str = "",
    resume_text: str = "",
) -> dict:
    raw_semantic = cosine_similarity_score(resume_embedding, job_embedding)
    semantic = _calibrate_semantic(raw_semantic)

    coverage, evidence, required, matched, missing = _skill_components(
        resume_text=resume_text,
        profile_skills=user_skills,
        job_text=job_text,
    )

    role = _role_alignment(resume_text, job_text)

    final = (
        0.55 * coverage
        + 0.30 * semantic
        + 0.00 * evidence
        + 0.15 * role
    )

    # When there is no trustworthy exact set, don't pretend skill confidence.
    if not required:
        final = 0.60 * semantic + 0.25 * role + 0.15 * 0.5

    final = max(0.0, min(1.0, final))

    return {
        "score": round(final * 100.0, 2),
        "semantic_raw": round(raw_semantic * 100.0, 2),
        "semantic_calibrated": round(semantic * 100.0, 2),
        "skill_coverage": round(coverage * 100.0, 2),
        "evidence_score": round(evidence * 100.0, 2),
        "role_alignment": round(role * 100.0, 2),
        "required_skills": required,
        "matched_skills": matched,
        "missing_skills": missing,
        "method": "hybrid_exact_v5",
        "note": "Relevance score, not hiring probability.",
    }


def calculate_match_score(
    resume_embedding: list[float] | None,
    job_embedding: list[float] | None,
    user_skills: list[str] | None = None,
    job_text: str = "",
    resume_text: str = "",
) -> float:
    return float(
        calculate_match_details(
            resume_embedding=resume_embedding,
            job_embedding=job_embedding,
            user_skills=user_skills,
            job_text=job_text,
            resume_text=resume_text,
        )["score"]
    )
