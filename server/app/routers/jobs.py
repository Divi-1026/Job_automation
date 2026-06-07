from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from datetime import datetime, timedelta
import asyncio

from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.job import Job
from app.models.platform_credential import PlatformCredential
from app.routers.users import get_current_user
from app.utils.skill_matcher import filter_jobs_by_skills
from app.services.scraper_service import manual_scrape
from app.utils.encryption import decrypt_password

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Track running auto-apply tasks per user
_auto_apply_tasks: dict[str, asyncio.Task] = {}

# ----------------------------------------------------------------------
# Scrape endpoints
# ----------------------------------------------------------------------

@router.post("/scrape", status_code=202)
async def trigger_scrape():
    """Manually trigger a global job scrape (runs immediately)."""
    asyncio.create_task(manual_scrape())
    return {"message": "Global scraping started. Jobs will appear shortly."}

@router.get("/")
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    source: str | None = Query(None, pattern="^(naukri|indeed|internshala)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_skills = current_user.skills or []
    if not user_skills:
        return {"total": 0, "skip": skip, "limit": limit, "jobs": [], "user_skills": []}

    three_days_ago = datetime.utcnow() - timedelta(days=3)
    stmt = select(Job).where(Job.scraped_at >= three_days_ago)
    if source:
        stmt = stmt.where(Job.source == source)
    stmt = stmt.order_by(Job.scraped_at.desc())
    result = await db.execute(stmt)
    all_jobs = result.scalars().all()

    job_dicts = []
    for j in all_jobs:
        job_dicts.append({
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
        })
    matched = filter_jobs_by_skills(job_dicts, user_skills)

    total = len(matched)
    paginated = matched[skip : skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "user_skills": user_skills,
        "jobs": paginated,
    }

@router.delete("/", status_code=204)
async def clear_all_jobs():
    """⚠️ Delete ALL jobs from the database (global)."""
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Job))
        await db.commit()
    return

# ----------------------------------------------------------------------
# Auto‑apply endpoints
# ----------------------------------------------------------------------

@router.post("/auto-apply")
async def auto_apply_jobs(
    max_applies: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_str = str(current_user.id)

    # Cancel any existing task for this user
    if user_id_str in _auto_apply_tasks and not _auto_apply_tasks[user_id_str].done():
        _auto_apply_tasks[user_id_str].cancel()
        await asyncio.sleep(0.5)

    # 1. Get Naukri credentials
    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "naukri"
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(400, "Naukri credentials not set. Please add them in profile.")

    email = cred.email
    password = decrypt_password(cred.password_encrypted)

    # 2. Get unapplied Naukri jobs from DB
    stmt = select(Job).where(
        Job.source == "naukri",
        Job.applied == False,
        Job.url.isnot(None)
    ).limit(max_applies)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    if not jobs:
        return {"message": "No unapplied Naukri jobs found", "results": []}

    # 3. Build user profile for auto-apply
    user_profile = {
        "years_of_experience": str(current_user.years_of_experience) if current_user.years_of_experience else "2",
        "current_role": current_user.current_role or "Software Engineer",
        "current_company": current_user.current_company or "Tech Solutions",
        "skills": current_user.skills or [],
        "highest_education": current_user.highest_education or "Bachelor of Technology",
        "full_name": current_user.full_name,
        "location": current_user.location or "Bangalore",
        "current_salary": "8 LPA",
        "expected_salary": "12 LPA",
        "notice_period": "15 - 30 Days"
    }

    # 4. Convert jobs to dict list
    jobs_list = [{"id": str(j.id), "title": j.title, "url": j.url} for j in jobs]

    # 5. Run auto-apply in a cancellable task
    from app.services.auto_apply import AutoApplyService

    async def run_auto_apply():
        def sync_run():
            service = AutoApplyService(email, password, user_profile)
            return service.run_auto_apply(jobs_list, max_applies)
        loop = asyncio.get_running_loop()
        results, successful_job_ids = await loop.run_in_executor(None, sync_run)
        return results, successful_job_ids

    task = asyncio.create_task(run_auto_apply())
    _auto_apply_tasks[user_id_str] = task

    try:
        results, successful_job_ids = await task
    except asyncio.CancelledError:
        return {"message": "Auto-apply cancelled by user", "results": []}
    finally:
        _auto_apply_tasks.pop(user_id_str, None)

    # 6. Mark successful jobs as applied in DB
    if successful_job_ids:
        await db.execute(
            update(Job).where(Job.id.in_(successful_job_ids)).values(applied=True)
        )
        await db.commit()

    return {
        "message": f"Auto-apply completed. Success: {len(successful_job_ids)}",
        "results": results
    }

@router.post("/auto-apply/cancel", status_code=200)
async def cancel_auto_apply(
    current_user: User = Depends(get_current_user),
):
    """Cancel the currently running auto-apply process for the logged‑in user."""
    user_id_str = str(current_user.id)
    task = _auto_apply_tasks.get(user_id_str)
    if task and not task.done():
        task.cancel()
        return {"message": "Auto-apply cancellation requested. It will stop shortly."}
    else:
        return {"message": "No running auto-apply process found."}