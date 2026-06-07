"""
Fuzzy skill matching utility for matching user skills with job skill_query.

Handles variations like:
- Python, python, PYTHON
- Node.js, nodejs, node, Node
- React, react, React.js
"""

from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)

# Similarity threshold: skills must be ≥80% similar to match
SIMILARITY_THRESHOLD = 80

# Known skill aliases/groups (for normalized matching)
SKILL_ALIASES = {
    "js": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "react.js", "reactjs"],
    "angular": ["angular", "angularjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "node": ["node", "node.js", "nodejs"],
    "python": ["python", "py"],
    "java": ["java"],
    "cplusplus": ["c++", "cpp"],
    "csharp": ["c#", "csharp", "c sharp"],
    "golang": ["go", "golang"],
    "rust": ["rust"],
    "ruby": ["ruby"],
    "php": ["php"],
    "sql": ["sql", "mysql", "postgresql", "postgres"],
    "mongodb": ["mongodb", "mongo"],
    "aws": ["aws", "amazon"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure", "microsoft azure"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git"],
    "linux": ["linux"],
    "windows": ["windows"],
    "macos": ["macos", "mac"],
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name for comparison (lowercase, strip whitespace)."""
    return skill.strip().lower()


def match_skills(user_skill: str, job_skill: str, threshold: int = SIMILARITY_THRESHOLD) -> bool:
    """
    Check if a user skill matches a job's skill_query using fuzzy matching.
    
    Args:
        user_skill: User's skill (e.g., "Python")
        job_skill: Job's skill_query from scraper (e.g., "python")
        threshold: Similarity threshold 0-100 (default 80)
    
    Returns:
        True if skills match with sufficient similarity, False otherwise
    """
    user_norm = normalize_skill(user_skill)
    job_norm = normalize_skill(job_skill)
    
    # Exact match (after normalization)
    if user_norm == job_norm:
        return True
    
    # Check aliases first (faster than fuzzy matching)
    for alias_group in SKILL_ALIASES.values():
        if user_norm in alias_group and job_norm in alias_group:
            return True
    
    # Fuzzy matching (for partially similar skills)
    similarity = fuzz.token_set_ratio(user_norm, job_norm)
    matched = similarity >= threshold
    
    if matched:
        logger.debug(
            f"Skill matched: '{user_skill}' ≈ '{job_skill}' "
            f"(similarity: {similarity}%)"
        )
    
    return matched


def filter_jobs_by_skills(jobs: list[dict], user_skills: list[str]) -> list[dict]:
    """
    Filter a list of jobs to only those matching user's skills.
    
    Args:
        jobs: List of job dicts with 'skill_query' field
        user_skills: List of user's skills
    
    Returns:
        Filtered list of jobs where skill_query fuzzy-matches at least one user skill
    """
    if not user_skills:
        return []  # No skills, no matches
    
    matched_jobs = []
    for job in jobs:
        job_skill = job.get("skill_query", "")
        if not job_skill:
            continue
        
        # Check if job's skill matches any of the user's skills
        for user_skill in user_skills:
            if match_skills(user_skill, job_skill):
                matched_jobs.append(job)
                break  # Skip other user skills for this job
    
    return matched_jobs
