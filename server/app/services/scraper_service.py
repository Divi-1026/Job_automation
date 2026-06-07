import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.job import Job
from app.scrapers.naukri import scrape_naukri
from app.scrapers.indeed import scrape_indeed
from app.scrapers.internshala import scrape_internshala

logger = logging.getLogger(__name__)

DEFAULT_SKILLS = [
    "Python", "JavaScript", "Java", "React", "Node.js", "Django",
    "AWS", "Docker", "SQL", "Machine Learning"
]
JOBS_PER_SKILL = 50
SCRAPE_INTERVAL = 30 * 60  # 30 minutes

async def save_jobs(jobs: List[dict]) -> int:
    """Save jobs to DB, skip duplicates by URL."""
    if not jobs:
        return 0
    saved = 0
    async with AsyncSessionLocal() as db:
        for job in jobs:
            # Check if URL already exists
            existing = await db.execute(select(Job).where(Job.url == job["url"]))
            if existing.scalar_one_or_none():
                continue
            new_job = Job(
                title=job["title"],
                company=job.get("company"),
                location=job.get("location"),
                salary=job.get("salary"),
                description=job.get("description"),
                url=job["url"],
                source=job["source"],
                skill_query=job.get("skill_query"),
                scraped_at=datetime.utcnow(),
            )
            db.add(new_job)
            saved += 1
        await db.commit()
    return saved

async def scrape_all_skills():
    """Run all scrapers for default skills."""
    logger.info("🔄 Starting global job scrape...")
    all_jobs = []
    try:
        naukri = await scrape_naukri(DEFAULT_SKILLS, JOBS_PER_SKILL)
        all_jobs.extend(naukri)
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Naukri error: {e}")
    try:
        indeed = await scrape_indeed(DEFAULT_SKILLS, JOBS_PER_SKILL)
        all_jobs.extend(indeed)
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Indeed error: {e}")
    try:
        internshala = await scrape_internshala(DEFAULT_SKILLS, JOBS_PER_SKILL)
        all_jobs.extend(internshala)
    except Exception as e:
        logger.error(f"Internshala error: {e}")
    saved = await save_jobs(all_jobs)
    logger.info(f"✅ Scraped {len(all_jobs)} jobs, saved {saved} new ones.")
    return saved

async def start_periodic_scraping():
    """Run scrape_all_skills every SCRAPE_INTERVAL seconds."""
    while True:
        try:
            await scrape_all_skills()
        except Exception as e:
            logger.exception(f"Scraping task crashed: {e}")
        await asyncio.sleep(SCRAPE_INTERVAL)

async def manual_scrape():
    """Manually trigger a scrape (for POST /jobs/scrape)."""
    await scrape_all_skills()