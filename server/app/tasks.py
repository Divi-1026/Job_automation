"""
Celery tasks for continuous job scraping and cleanup.

Tasks:
  - scrape_all_skills_task(): Scrapes jobs from all platforms for popular skills
  - cleanup_expired_jobs_task(): Deletes jobs older than 2 days daily
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from app.celery_config import celery_app
from app.database import AsyncSessionLocal
from app.models.job import Job
from app.scrapers.naukri import scrape_naukri
from app.scrapers.indeed import scrape_indeed
from app.scrapers.internshala import scrape_internshala
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# Popular tech skills to scrape (hardcoded list)
# TODO: Later migrate to dynamic top-N from all users' skills
DEFAULT_SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "C++",
    "C#",
    "PHP",
    "Ruby",
    "Go",
    "Rust",
    "TypeScript",
    "React",
    "Angular",
    "Vue.js",
    "Node.js",
    "Django",
    "FastAPI",
    "Flask",
    "Spring Boot",
    "SQL",
    "PostgreSQL",
    "MongoDB",
    "AWS",
    "Docker",
    "Kubernetes",
    "Git",
    "Linux",
    "Machine Learning",
    "Data Science",
    "AI",
]

JOBS_PER_SKILL = 10
DELAY_BETWEEN_SKILLS = 2  # seconds, reduced for faster scraping


async def _get_db_session():
    """Get a new async database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def _save_jobs_to_db(jobs: List[dict]) -> int:
    """
    Save scraped jobs to database.
    Returns the number of jobs successfully saved (ignoring duplicates).
    """
    if not jobs:
        return 0

    saved_count = 0
    async with AsyncSessionLocal() as session:
        for job_data in jobs:
            try:
                # Create Job object with expires_at = now + 2 days
                job = Job(
                    title=job_data.get("title"),
                    company=job_data.get("company"),
                    location=job_data.get("location"),
                    salary=job_data.get("salary"),
                    description=job_data.get("description"),
                    url=job_data.get("url"),
                    source=job_data.get("source"),
                    skill_query=job_data.get("skill_query"),
                    scraped_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=3),
                )
                session.add(job)
                await session.commit()
                saved_count += 1
                logger.debug(
                    f"Saved job: {job.title} from {job.source} (skill: {job.skill_query})"
                )
            except IntegrityError:
                # Duplicate job (unique constraint on url, source, skill_query)
                await session.rollback()
                logger.debug(
                    f"Duplicate job skipped: {job_data.get('url')} "
                    f"({job_data.get('source')})"
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"Error saving job: {e}")

    return saved_count

@celery_app.task(bind=True, name="app.tasks.scrape_for_user_skills_task")
def scrape_for_user_skills_task(self, user_id: str, skills: List[str]):
    """
    Scrape jobs for a specific user's skills (triggered after signup).
    Runs asynchronously so signup is not blocked.
    """
    logger.info(f"🔄 Starting user-specific scraping for user {user_id} with skills: {skills}")
    if not skills:
        logger.info(f"No skills for user {user_id}, skipping scraping.")
        return {"status": "skipped", "reason": "no skills"}
    
    try:
        all_jobs = asyncio.run(_scrape_for_skills(skills))
        saved = asyncio.run(_save_jobs_to_db(all_jobs))
        logger.info(f"✅ User {user_id} scraping complete: {len(all_jobs)} jobs, {saved} saved")
        return {
            "status": "success",
            "user_id": user_id,
            "skills": skills,
            "jobs_scraped": len(all_jobs),
            "jobs_saved": saved,
        }
    except Exception as e:
        logger.error(f"❌ User scraping failed for {user_id}: {e}", exc_info=True)
        raise

async def _scrape_for_skills(skills: List[str]) -> List[dict]:
    """Scrape jobs for given skills from all platforms."""
    all_jobs = []
    JOBS_PER_SKILL = 10
    try:
        naukri_jobs = await scrape_naukri(skills, max_per_skill=JOBS_PER_SKILL)
        all_jobs.extend(naukri_jobs)
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Naukri failed for user skills: {e}")
    
    try:
        indeed_jobs = await scrape_indeed(skills, max_per_skill=JOBS_PER_SKILL)
        all_jobs.extend(indeed_jobs)
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Indeed failed for user skills: {e}")
    
    try:
        internshala_jobs = await scrape_internshala(skills, max_per_skill=JOBS_PER_SKILL)
        all_jobs.extend(internshala_jobs)
    except Exception as e:
        logger.error(f"Internshala failed for user skills: {e}")
    
    return all_jobs

@celery_app.task(bind=True, name="app.tasks.scrape_all_skills_task")
def scrape_all_skills_task(self):
    """
    Main scraping task — scrapes jobs from all platforms for popular skills.
    
    Runs continuously (every 30 minutes via beat schedule).
    Calls all three scrapers sequentially and saves results to database.
    """
    logger.info("🔄 Starting job scraping task...")
    try:
        # Run async scrapers
        all_jobs = asyncio.run(_scrape_all_platforms())
        
        # Save to database
        saved = asyncio.run(_save_jobs_to_db(all_jobs))
        
        total = len(all_jobs)
        logger.info(
            f"✅ Scraping complete: {total} jobs scraped, "
            f"{saved} saved to DB ({total - saved} duplicates)"
        )
        
        return {
            "status": "success",
            "total_jobs_scraped": total,
            "jobs_saved": saved,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"❌ Scraping task failed: {e}", exc_info=True)
        # Re-raise so Celery can retry
        raise


async def _scrape_all_platforms() -> List[dict]:
    """Call all three scrapers and combine results."""
    all_jobs = []
    
    logger.info(f"📍 Scraping {len(DEFAULT_SKILLS)} skills from 3 platforms...")
    
    try:
        # Naukri
        logger.info("🔗 Starting Naukri scrape...")
        naukri_jobs = await scrape_naukri(DEFAULT_SKILLS, max_per_skill=JOBS_PER_SKILL)
        all_jobs.extend(naukri_jobs)
        logger.info(f"✓ Naukri: {len(naukri_jobs)} jobs scraped")
        await asyncio.sleep(DELAY_BETWEEN_SKILLS)
    except Exception as e:
        logger.error(f"❌ Naukri scraping failed: {e}")
    
    try:
        # Indeed
        logger.info("🔗 Starting Indeed scrape...")
        indeed_jobs = await scrape_indeed(DEFAULT_SKILLS, max_per_skill=JOBS_PER_SKILL)
        all_jobs.extend(indeed_jobs)
        logger.info(f"✓ Indeed: {len(indeed_jobs)} jobs scraped")
        await asyncio.sleep(DELAY_BETWEEN_SKILLS)
    except Exception as e:
        logger.error(f"❌ Indeed scraping failed: {e}")
    
    try:
        # Internshala
        logger.info("🔗 Starting Internshala scrape...")
        internshala_jobs = await scrape_internshala(
            DEFAULT_SKILLS, max_per_skill=JOBS_PER_SKILL
        )
        all_jobs.extend(internshala_jobs)
        logger.info(f"✓ Internshala: {len(internshala_jobs)} jobs scraped")
    except Exception as e:
        logger.error(f"❌ Internshala scraping failed: {e}")
    
    return all_jobs


@celery_app.task(bind=True, name="app.tasks.cleanup_expired_jobs_task")
def cleanup_expired_jobs_task(self):
    """
    Daily cleanup task — deletes jobs older than 2 days.
    
    Runs daily at 2 AM UTC (via beat schedule).
    """
    logger.info("🧹 Starting job cleanup task...")
    try:
        deleted_count = asyncio.run(_delete_expired_jobs())
        logger.info(f"✅ Cleanup complete: {deleted_count} expired jobs deleted")
        
        return {
            "status": "success",
            "deleted_jobs": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"❌ Cleanup task failed: {e}", exc_info=True)
        raise


async def _delete_expired_jobs() -> int:
    """Delete all jobs where expires_at < now. Returns deleted count."""
    async with AsyncSessionLocal() as session:
        try:
            # Query expired jobs
            result = await session.execute(
                delete(Job).where(Job.expires_at < datetime.utcnow())
            )
            deleted_count = result.rowcount
            await session.commit()
            
            logger.info(f"Deleted {deleted_count} expired job(s)")
            return deleted_count
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting expired jobs: {e}")
            raise
