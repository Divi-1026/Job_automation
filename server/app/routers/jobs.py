"""
Jobs router — scrape and fetch jobs for the authenticated user.

Background loop behaviour
─────────────────────────
• Starts automatically when the user logs in or signs up
  (call start_user_scraper(user_id) from the auth router).
• Picks skills ONE AT A TIME from the user's profile.
• Scrapes exactly 5 Naukri jobs per skill, then moves to the next skill.
• After all skills are processed it loops back to the first skill.
• Runs until stop_user_scraper(user_id) is called (on logout).
• One shared Playwright browser per user — cookies / session persist.

Endpoints
─────────
POST   /jobs/scrape   → manually (re)start the loop
GET    /jobs          → list all scraped jobs (optional ?source= filter)
DELETE /jobs          → clear all jobs for the user
"""

import asyncio
import uuid
import random
import logging
from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.job import Job
from app.routers.users import get_current_user
from app.scrapers.naukri import scrape_one_skill, _make_browser_page
from app.scrapers.indeed import scrape_one_skill_indeed
from app.scrapers.internshala import scrape_internshala

from playwright.async_api import async_playwright

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Seconds to wait between scraping each skill
DELAY_BETWEEN_SKILLS = 5        # short pause between skills
DELAY_BETWEEN_CYCLES = 60 * 10  # 10-min rest after finishing all skills

JOBS_PER_SKILL = 10   # how many jobs to fetch per skill per source

# user_id (str) → running asyncio.Task
_active_scrapers: dict[str, asyncio.Task] = {}


def _task_done_cb(task: asyncio.Task):
    """Log unhandled exceptions from background scrape tasks."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error(f"[Scraper] Background task crashed: {exc!r}", exc_info=exc)


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def _persist_jobs(user_id: uuid.UUID, raw_jobs: list[dict], db: AsyncSession):
    """Insert jobs, silently ignoring duplicates (same user + URL)."""
    if not raw_jobs:
        return
    for j in raw_jobs:
        stmt = (
            pg_insert(Job)
            .values(
                user_id=user_id,
                title=j["title"],
                company=j.get("company"),
                location=j.get("location"),
                salary=j.get("salary"),
                description=j.get("description"),
                url=j.get("url"),
                source=j["source"],
                skill_query=j.get("skill_query"),
            )
            .on_conflict_do_nothing(constraint="uq_user_job_url")
        )
        await db.execute(stmt)
    await db.commit()


async def _get_user_skills(user_id: uuid.UUID) -> list[str] | None:
    """
    Fetch fresh skills from DB.
    Returns None if user not found / deactivated (signals loop to stop).
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user_obj = result.scalar_one_or_none()
        if not user_obj or not user_obj.is_active:
            return None
        return user_obj.skills or []


# ── Core loop — one skill at a time ───────────────────────────────────────────

async def _scrape_loop(user_id: uuid.UUID):
    """
    Continuously scrape Naukri + Internshala one skill at a time.

    Flow per iteration:
      1. Load user's skills from DB (picks up any profile updates).
      2. Iterate through skills one by one:
           a. Scrape JOBS_PER_SKILL Naukri jobs for that skill (Playwright).
           b. Scrape JOBS_PER_SKILL Internshala jobs for that skill (httpx).
           c. Persist to DB.
           d. Wait DELAY_BETWEEN_SKILLS seconds.
      3. After all skills are done, wait DELAY_BETWEEN_CYCLES seconds.
      4. Repeat from step 1.
    """
    logger.info(f"[Scraper] Loop started for user {user_id}")
    async with async_playwright() as pw:
        browser, page = await _make_browser_page(pw)
        logger.info(f"[Scraper] Browser ready for user {user_id}")

        try:
            while True:
                # ── 1. Fetch latest skills ─────────────────────────────────
                skills = await _get_user_skills(user_id)

                if skills is None:
                    logger.info(f"[Scraper] User {user_id} not found or deactivated — stopping loop.")
                    break

                if not skills:
                    logger.info(f"[Scraper] User {user_id} has no skills yet — retrying in 60s.")
                    await asyncio.sleep(60)
                    continue

                logger.info(f"[Scraper] Starting cycle for user {user_id} — {len(skills)} skill(s): {skills}")

                # ── 2. Scrape one skill at a time ──────────────────────────
                for skill in skills:
                    try:
                        await asyncio.sleep(0)   # yield to event loop
                    except asyncio.CancelledError:
                        raise

                    all_jobs: list[dict] = []

                    # ── 2a. Naukri (Playwright / Firefox) ──────────────────
                    logger.info(f"[Scraper] Naukri — scraping '{skill}' for user {user_id}")
                    try:
                        naukri_jobs = await scrape_one_skill(
                            skill=skill,
                            max_jobs=JOBS_PER_SKILL,
                            page=page,
                        )
                        all_jobs.extend(naukri_jobs)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"[Scraper] Naukri error for '{skill}': {e}")

                    # ── 2b. Indeed (Playwright / Firefox — same page) ─────
                    logger.info(f"[Scraper] Indeed — scraping '{skill}' for user {user_id}")
                    try:
                        indeed_jobs = await scrape_one_skill_indeed(
                            skill=skill,
                            max_jobs=JOBS_PER_SKILL,
                            page=page,
                        )
                        all_jobs.extend(indeed_jobs)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"[Scraper] Indeed error for '{skill}': {e}")

                    # ── 2c. Internshala (httpx — lightweight) ─────────────
                    logger.info(f"[Scraper] Internshala — scraping '{skill}' for user {user_id}")
                    try:
                        internshala_jobs = await scrape_internshala(
                            skills=[skill],
                            max_per_skill=JOBS_PER_SKILL,
                        )
                        all_jobs.extend(internshala_jobs)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"[Scraper] Internshala error for '{skill}': {e}")

                    logger.info(f"[Scraper] Got {len(all_jobs)} job(s) for '{skill}' — user {user_id}")

                    if all_jobs:
                        async with AsyncSessionLocal() as db:
                            await _persist_jobs(user_id, all_jobs, db)
                        logger.info(f"[Scraper] Persisted {len(all_jobs)} job(s) for '{skill}'")

                    try:
                        await asyncio.sleep(DELAY_BETWEEN_SKILLS)
                    except asyncio.CancelledError:
                        raise

                logger.info(f"[Scraper] Cycle complete for user {user_id} — resting {DELAY_BETWEEN_CYCLES}s before next cycle.")

                # ── 3. All skills done — rest before next cycle ────────────
                for _ in range(DELAY_BETWEEN_CYCLES // 10):
                    await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info(f"[Scraper] Loop cancelled for user {user_id} (logged out).")
        finally:
            try:
                await browser.close()
                logger.info(f"[Scraper] Browser closed for user {user_id}.")
            except Exception:
                pass


# ── Scraper lifecycle ─────────────────────────────────────────────────────────

def start_user_scraper(user_id: uuid.UUID):
    """
    Start (or restart) the background scrape loop for a user.
    Called automatically from the auth router on login / signup.
    """
    key = str(user_id)
    existing = _active_scrapers.get(key)
    if existing and not existing.done():
        logger.info(f"[Scraper] Restarting existing loop for user {user_id}")
        existing.cancel()
    task = asyncio.create_task(_scrape_loop(user_id))
    task.add_done_callback(_task_done_cb)
    _active_scrapers[key] = task
    logger.info(f"[Scraper] Task created for user {user_id}")


def stop_user_scraper(user_id: uuid.UUID):
    """
    Cancel the scrape loop for a user.
    Called automatically from the auth router on logout.
    """
    key = str(user_id)
    task = _active_scrapers.pop(key, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"[Scraper] Task cancelled for user {user_id}")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/scrape", status_code=202)
async def trigger_scrape(
    current_user: User = Depends(get_current_user),
):
    """
    Manually (re)start the scrape loop.
    The loop starts automatically on login — this endpoint is for manual resets.
    """
    start_user_scraper(current_user.id)

    if not (current_user.skills or []):
        return {
            "message": (
                "Loop started. No skills on your profile yet — "
                "add skills in Profile and jobs will start appearing."
            )
        }

    return {
        "message": (
            f"Scraping {len(current_user.skills)} skill(s) from Naukri + Indeed + Internshala, "
            f"{JOBS_PER_SKILL} jobs each. Jobs will appear shortly."
        )
    }


@router.get("/", summary="List scraped jobs")
async def list_jobs(
    source: str | None = Query(None, description="Filter by source: 'naukri', 'indeed', 'internshala'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).where(Job.user_id == current_user.id)
    if source:
        stmt = stmt.where(Job.source == source.lower())
    stmt = stmt.order_by(Job.scraped_at.desc())
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return [
        {
            "id":          str(j.id),
            "title":       j.title,
            "company":     j.company,
            "location":    j.location,
            "salary":      j.salary,
            "description": j.description,
            "url":         j.url,
            "source":      j.source,
            "skill_query": j.skill_query,
            "scraped_at":  j.scraped_at.isoformat() if j.scraped_at else None,
        }
        for j in jobs
    ]


@router.delete("/", status_code=204, summary="Clear all scraped jobs for the user")
async def clear_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(Job).where(Job.user_id == current_user.id))
    await db.commit()