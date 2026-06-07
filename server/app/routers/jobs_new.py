"""
Jobs router — query global job pool matched by user skills.

The job scraping system changed from per-user (on login) to global (continuous Celery tasks).

Now:
  • Jobs are scraped globally every 30 minutes by Celery workers.
  • All jobs are stored in a single shared pool.
  • When a user queries /jobs, they get jobs matching their skills via fuzzy matching.
  • Old jobs (>2 days) are deleted automatically by a daily Celery task.

Endpoints
─────────
GET    /jobs       → list jobs matching user's skills (global pool)
GET    /jobs/status → (optional) show scraping stats
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.routers.users import get_current_user
from app.utils.skill_matcher import filter_jobs_by_skills

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", summary="List jobs matching user's skills")
async def list_jobs(
    skip: int = Query(0, ge=0, description="Pagination: skip N jobs"),
    limit: int = Query(20, ge=1, le=100, description="Pagination: return N jobs"),
    source: str | None = Query(None, description="Filter by source: 'naukri', 'indeed', 'internshala'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get global jobs matching the current user's skills.
    
    Jobs are filtered using fuzzy skill matching:
      - Python matches python, py, PYTHON, etc.
      - Node.js matches node, nodejs, node.js, etc.
    
    Returns paginated results sorted by most recently scraped.
    """
    # Get user's skills (or empty list if none)
    user_skills = current_user.skills or []
    
    if not user_skills:
        return {
            "total": 0,
            "skip": skip,
            "limit": limit,
            "jobs": [],
            "message": (
                "You haven't added any skills yet. "
                "Add skills to your profile to see matching jobs."
            ),
        }
    
    # Query all non-expired global jobs from database
    query = select(Job).where(Job.expires_at > datetime.utcnow())
    
    if source:
        query = query.where(Job.source == source.lower())
    
    query = query.order_by(desc(Job.scraped_at))
    
    result = await db.execute(query)
    all_jobs = result.scalars().all()
    
    # Convert ORM objects to dicts for skill matching
    job_dicts = [
        {
            "id": str(j.id),
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "salary": j.salary,
            "description": j.description,
            "url": j.url,
            "source": j.source,
            "skill_query": j.skill_query,
            "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
            "expires_at": j.expires_at.isoformat() if j.expires_at else None,
        }
        for j in all_jobs
    ]
    
    # Filter jobs by fuzzy skill matching
    matched_jobs = filter_jobs_by_skills(job_dicts, user_skills)
    
    # Apply pagination
    total = len(matched_jobs)
    paginated_jobs = matched_jobs[skip : skip + limit]
    
    logger.info(
        f"User {current_user.id} queried jobs: "
        f"skills={user_skills}, matched={total}, returned={len(paginated_jobs)}"
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "user_skills": user_skills,
        "jobs": paginated_jobs,
    }


@router.get("/status", summary="Job scraping status")
async def job_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get global scraping status (informational endpoint).
    
    Returns:
      - Total jobs in database
      - Jobs expiring soon (< 24 hours)
      - Last scrape time (from most recent job)
    """
    # Count total jobs
    result = await db.execute(select(Job))
    total_jobs = len(result.scalars().all())
    
    # Find most recent job (last scrape time)
    result = await db.execute(
        select(Job).order_by(desc(Job.scraped_at)).limit(1)
    )
    latest_job = result.scalar_one_or_none()
    last_scrape_time = latest_job.scraped_at.isoformat() if latest_job else None
    
    # Count expiring soon (< 24 hours)
    from datetime import timedelta
    expiring_threshold = datetime.utcnow() + timedelta(hours=24)
    result = await db.execute(
        select(Job).where(
            and_(
                Job.expires_at > datetime.utcnow(),
                Job.expires_at < expiring_threshold,
            )
        )
    )
    expiring_soon = len(result.scalars().all())
    
    return {
        "total_jobs": total_jobs,
        "last_scrape_time": last_scrape_time,
        "jobs_expiring_soon_24h": expiring_soon,
        "message": (
            "Jobs are scraped every 30 minutes from Naukri, Indeed, and Internshala. "
            "Jobs expire after 2 days. Cleanup runs daily at 2 AM UTC."
        ),
    }
