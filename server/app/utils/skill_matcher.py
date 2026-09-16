"""
Legacy skill matcher.

CareerSync now uses semantic resume-to-job matching
for recommendations.

This module remains temporarily for compatibility
with older code paths.
"""

from fuzzywuzzy import fuzz


def normalize_skill(
    skill: str
) -> str:

    return (
        skill
        .strip()
        .lower()
    )


def match_skills(
    user_skill: str,
    job_skill: str,
    threshold: int = 80,
) -> bool:

    if not user_skill or not job_skill:

        return False


    user_norm = normalize_skill(
        user_skill
    )

    job_norm = normalize_skill(
        job_skill
    )


    if user_norm == job_norm:

        return True


    similarity = (
        fuzz.token_set_ratio(
            user_norm,
            job_norm
        )
    )


    return (
        similarity
        >= threshold
    )


def filter_jobs_by_skills(
    jobs: list[dict],
    user_skills: list[str],
) -> list[dict]:
    """
    Legacy fallback.

    This must NOT be used by the final /jobs
    recommendation endpoint.
    """

    if not user_skills:

        return []


    matched = []


    for job in jobs:

        skill = (
            job.get(
                "skill_query"
            )
            or ""
        )


        if any(

            match_skills(
                user_skill,
                skill
            )

            for user_skill
            in user_skills

        ):

            matched.append(
                job
            )


    return matched