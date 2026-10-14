"""
CareerSync global scrape + save task.

Platforms:
    Naukri
    Internshala

Search queries are discovery metadata ONLY:
    React.js
    Express.js
    Frontend Developer
    Backend Developer

Each platform tries to collect 5 UNIQUE jobs per query.

Job embedding is generated ONCE before DB save from:
    title + company + location + clean structured description

skill_query is deliberately excluded from embedding.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.celery_config import celery_app
from app.database import AsyncSessionLocal
from app.models.job import Job
from app.scrapers.naukri import scrape_naukri
from app.scrapers.internshala import scrape_internshala
from app.utils.semantic_match import create_embedding
from app.scrapers.indeed import scrape_indeed


logger = logging.getLogger(__name__)


DEFAULT_SKILLS = [
    # Core Engineering Roles
    "Software Engineer",
    "Software Developer",
    # AI & Machine Learning Roles
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Generative AI Engineer",
    "Deep Learning",
    "NLP Engineer",
   
    # Frontend
    "React.js",
    "Next.js",
    "TypeScript",
    "Frontend Developer",
    # Backend & Full Stack
    "Node.js",
    "Express.js",
    "Full Stack Developer",
    "Backend Developer",
    # Databases & DevOps/Cloud
    "MongoDB",
    "PostgreSQL",
    "Docker",
    "AWS",
]

JOBS_PER_SKILL = 2
DELAY_BETWEEN_PLATFORMS = 2


def build_job_text(job_data: dict) -> str:
    """
    Exact text embedded once and later compared with saved resume embedding.

    Normal Naukri Platform Key Skills remain inside description, so they may
    contribute semantically, but they do NOT enter exact skill coverage.
    """
    return "\n".join(
        [
            f"Job title: {job_data.get('title') or ''}",
            f"Company: {job_data.get('company') or ''}",
            f"Location: {job_data.get('location') or ''}",
            f"Description: {job_data.get('description') or ''}",
        ]
    )


async def _scrape_all_platforms() -> List[dict]:
    all_jobs: list[dict] = []

    for platform_name, scraper in (
        ("naukri", scrape_naukri),
        ("internshala", scrape_internshala),
        ("indeed", scrape_indeed),
    ):
        try:
            logger.info(
                "Starting %s scrape | queries=%d | max_per_query=%d",
                platform_name,
                len(DEFAULT_SKILLS),
                JOBS_PER_SKILL,
            )

            jobs = await scraper(
                DEFAULT_SKILLS,
                max_per_skill=JOBS_PER_SKILL,
            )
            jobs = jobs or []

            valid = []
            for job in jobs:
                if not isinstance(job, dict):
                    continue

                url = str(job.get("url") or "").strip()
                if not url:
                    logger.warning(
                        "Skipping %s job without URL | %s",
                        platform_name,
                        job.get("title"),
                    )
                    continue

                description = str(job.get("description") or "").strip()
                if not description:
                    logger.warning(
                        "%s job has empty clean description | %s",
                        platform_name,
                        job.get("title"),
                    )

                job["source"] = platform_name
                valid.append(job)

            all_jobs.extend(valid)

            logger.info(
                "%s scrape finished | jobs=%d",
                platform_name,
                len(valid),
            )

        except Exception as exc:
            logger.exception(
                "%s scrape failed; continuing: %s",
                platform_name,
                exc,
            )

        if DELAY_BETWEEN_PLATFORMS:
            await asyncio.sleep(DELAY_BETWEEN_PLATFORMS)

    logger.info(
        "Global scrape collection finished | total_records=%d",
        len(all_jobs),
    )
    return all_jobs


async def _save_jobs_to_db(jobs: List[dict]) -> int:
    if not jobs:
        logger.warning("No scraped jobs received for DB save.")
        return 0

    unique_jobs = []
    seen_urls = set()

    for raw in jobs:
        job = dict(raw)
        url = str(job.get("url") or "").strip().rstrip("/")
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        job["url"] = url
        unique_jobs.append(job)

    if not unique_jobs:
        return 0

    saved_count = 0

    async with AsyncSessionLocal() as session:
        existing_result = await session.execute(
            select(Job.url).where(
                Job.url.in_([job["url"] for job in unique_jobs])
            )
        )

        existing_urls = {
            str(url).rstrip("/")
            for url in existing_result.scalars().all()
            if url
        }

        new_jobs = [
            job for job in unique_jobs
            if job["url"] not in existing_urls
        ]

        logger.info(
            "DB ingestion | scraped=%d unique=%d existing=%d new=%d",
            len(jobs),
            len(unique_jobs),
            len(existing_urls),
            len(new_jobs),
        )

        for job_data in new_jobs:
            now = datetime.utcnow()

            try:
                embedding_text = build_job_text(job_data)
                embedding = create_embedding(embedding_text)
            except Exception as exc:
                embedding = None
                logger.exception(
                    "Embedding failed; saving row without embedding | %s | %s",
                    job_data.get("url"),
                    exc,
                )

            try:
                row = Job(
                    title=job_data.get("title") or "Untitled Job",
                    company=job_data.get("company"),
                    location=job_data.get("location"),
                    salary=job_data.get("salary"),
                    description=job_data.get("description"),
                    url=job_data.get("url"),
                    source=job_data.get("source"),
                    skill_query=job_data.get("skill_query"),
                    embedding=embedding,
                    scraped_at=now,
                    expires_at=now + timedelta(days=7),
                )

                session.add(row)
                await session.commit()
                saved_count += 1

                logger.info(
                    "SAVED %d/%d | %s | %s | %s | embedding=%s",
                    saved_count,
                    len(new_jobs),
                    row.source,
                    row.skill_query,
                    row.title,
                    "yes" if embedding else "no",
                )

            except IntegrityError:
                await session.rollback()
                logger.info("Duplicate skipped during insert | %s", job_data.get("url"))

            except Exception as exc:
                await session.rollback()
                logger.exception(
                    "DB SAVE FAILED | %s | %s",
                    job_data.get("url"),
                    exc,
                )

    logger.info(
        "DB save finished | requested_new=%d saved=%d",
        len(new_jobs),
        saved_count,
    )
    return saved_count


async def _run_scrape_and_save_cycle():
    jobs = await _scrape_all_platforms()
    saved = await _save_jobs_to_db(jobs)
    return jobs, saved


@celery_app.task(
    bind=True,
    name="app.tasks.scrape_all_skills_task",
)
def scrape_all_skills_task(self):
    logger.info("Starting daily global job scrape")

    jobs, saved = asyncio.run(_run_scrape_and_save_cycle())

    logger.info(
        "SCRAPE COMPLETE | scraped=%d | saved=%d | skipped/duplicate=%d",
        len(jobs),
        saved,
        max(0, len(jobs) - saved),
    )

    return {
        "status": "success",
        "total_jobs_scraped": len(jobs),
        "jobs_saved": saved,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _cleanup_expired_jobs_async() -> dict:
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()

        # Pehle expired jobs nikalo
        result = await session.execute(
            select(Job).where(Job.expires_at < now)
        )

        expired_jobs = result.scalars().all()

        # Deleted jobs print/log karo
        for job in expired_jobs:
            logger.info(
                "DELETING EXPIRED JOB | id=%s | title=%s | company=%s | expires_at=%s | url=%s",
                job.id,
                job.title,
                job.company,
                job.expires_at,
                job.url,
            )
            print(
                f"DELETING: {job.title} | "
                f"{job.company} | "
                f"expires_at={job.expires_at} | "
                f"url={job.url}"
            )

        # Ab delete karo
        await session.execute(
            delete(Job).where(Job.expires_at < now)
        )

        await session.commit()

        return {
            "status": "success",
            "deleted": len(expired_jobs),
            "timestamp": now.isoformat(),
        }
@celery_app.task(name="app.tasks.cleanup_expired_jobs_task")
def cleanup_expired_jobs_task():
    return asyncio.run(_cleanup_expired_jobs_async())
