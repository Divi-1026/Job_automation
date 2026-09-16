"""
Jobs router.

FINAL ARCHITECTURE
------------------

Celery Beat
    ↓
Global scraping
    ↓
Naukri + Indeed + Internshala
    ↓
GLOBAL Job table
    ↓
Job embedding stored once


User uploads resume
    ↓
Resume parsed once
    ↓
Resume embedding stored in User


GET /jobs
    ↓
NO SCRAPING
    ↓
Read global jobs
    ↓
Saved Resume embedding
        VS
Saved Job embedding
    ↓
Semantic similarity
    ↓
Confidence score
    ↓
Sort DESC
"""

import asyncio
import logging
import re

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from sqlalchemy import (
    select,
    desc,
    and_,
    or_,
    String,
)

from app.database import get_db

from app.models.user import User
from app.models.job import Job
from app.models.user_application import UserApplication
from app.models.platform_credential import (
    PlatformCredential,
)

from app.routers.users import (
    get_current_user,
)

from app.utils.semantic_match import (
    create_embedding,
    calculate_match_score,
    calculate_match_details,
)

from app.utils.encryption import (
    decrypt_password,
)





logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


# Track auto-apply process separately for every user.
_auto_apply_tasks: dict[
    str,
    asyncio.Task
] = {}


# =========================================================
# HELPER
# =========================================================

def build_job_text(
    job: Job
) -> str:
    """
    Convert job information into text used
    for semantic embedding/matching.
    """

    parts = [
        f"Job title: {job.title or ''}",
        f"Company: {job.company or ''}",
        f"Location: {job.location or ''}",
        # IMPORTANT: skill_query is only the scraper discovery keyword.
        # It is NOT a verified job requirement and must not affect ranking.
        f"Description: {job.description or ''}",
    ]

    return "\n".join(parts)


def _print_matching_debug(
    *,
    platform: str,
    job: Job,
    details: dict,
    embedding_source: str = "stored",
) -> None:
    """Print one concise explainable block per job without leaking resume text."""
    print("\n" + "=" * 90, flush=True)
    print(f"[MATCH DEBUG] PLATFORM: {platform}", flush=True)
    print(f"[MATCH DEBUG] JOB ID: {job.id}", flush=True)
    print(f"[MATCH DEBUG] TITLE: {job.title or ''}", flush=True)
    print(f"[MATCH DEBUG] COMPANY: {job.company or ''}", flush=True)
    print(f"[MATCH DEBUG] LOCATION: {job.location or ''}", flush=True)
    print(f"[MATCH DEBUG] JOB EMBEDDING: {embedding_source}", flush=True)
    print(f"RAW COSINE: {details['semantic_raw']:.2f}%", flush=True)
    print(f"CALIBRATED SEMANTIC: {details['semantic_calibrated']:.2f}%", flush=True)
    print(f"REQUIRED SKILL COVERAGE: {details['skill_coverage']:.2f}%", flush=True)
    print(f"RESUME EVIDENCE: {details['evidence_score']:.2f}%", flush=True)
    print(f"ROLE ALIGNMENT: {details['role_alignment']:.2f}%", flush=True)
    print(f"REQUIRED SKILLS: {details['required_skills'] or 'None'}", flush=True)
    print(f"MATCHED SKILLS: {details['matched_skills'] or 'None'}", flush=True)
    print(f"MISSING SKILLS: {details['missing_skills'] or 'None'}", flush=True)
    print(f"FINAL MATCH SCORE: {details['score']:.2f}%", flush=True)
    print("=" * 90 + "\n", flush=True)


# =========================================================
# GET RECOMMENDED JOBS
# =========================================================

@router.get(
    "/",
    summary="Get semantic job recommendations",
)
async def list_jobs(

    skip: int = Query(
        0,
        ge=0,
    ),

    limit: int = Query(
        100,
        ge=1,
        le=500,
    ),

    source: str | None = Query(
        None,
        pattern="^(naukri|indeed|internshala)$",
    ),

    min_score: float = Query(
        0,
        ge=0,
        le=100,
    ),

    location: str | None = Query(
        None,
    ),

    search: str | None = Query(
        None,
    ),

    # Exact frontend-visible Naukri job IDs.
    # When provided, auto-apply is NOT allowed to jump to any other DB job.
    job_ids: str | None = Query(
        None,
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Return active GLOBAL jobs ranked for the logged-in user.

    Applied and pending-manual jobs are user-specific and are
    excluded from recommendations so they do not appear again.
    """

    if (
        not current_user.resume_text
        or not current_user.resume_embedding
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Please upload your resume first "
                "to receive personalized job matches."
            ),
        )

    user_id_str = str(
        current_user.id
    )

    # -----------------------------------------------------
    # Jobs already handled by THIS user
    # -----------------------------------------------------

    history_result = await db.execute(

        select(
            UserApplication.job_id
        ).where(

            UserApplication.user_id
            == user_id_str,

            UserApplication.status.in_(
                [
                    "applied",
                    "pending_manual",
                    "not_eligible",
                    "needs_review",
                ]
            ),
        )
    )

    excluded_job_ids = set(
        history_result.scalars().all()
    )

    # -----------------------------------------------------
    # Query active global jobs
    # -----------------------------------------------------

    query = select(Job).where(
        Job.expires_at
        > datetime.utcnow()
    )

    if source:

        query = query.where(
            Job.source
            == source.lower()
        )

    if location:

        query = query.where(
            Job.location.ilike(
                f"%{location.strip()}%"
            )
        )

    if search:

        search_value = (
            search.strip()
        )

        query = query.where(

            or_(

                Job.title.ilike(
                    f"%{search_value}%"
                ),

                Job.description.ilike(
                    f"%{search_value}%"
                ),
            )
        )

    result = await db.execute(
        query
    )

    all_active_jobs = (
        result.scalars().all()
    )

    # Do NOT delete these jobs from the global table.
    # They may still be useful to another user.
    global_jobs = [

        job

        for job in all_active_jobs

        if str(job.id)
        not in excluded_job_ids
    ]

    logger.info(
        "Semantic ranking user=%s active=%d excluded=%d remaining=%d",
        current_user.id,
        len(all_active_jobs),
        len(excluded_job_ids),
        len(global_jobs),
    )

    # -----------------------------------------------------
    # Rank jobs
    # -----------------------------------------------------

    ranked_jobs = []

    embeddings_updated = False

    for job in global_jobs:

        try:

            job_text = build_job_text(
                job
            )

            if not job.embedding:

                job_embedding = (
                    create_embedding(
                        job_text
                    )
                )

                job.embedding = (
                    job_embedding
                )

                embeddings_updated = True
                embedding_source = "generated now from EXACT JOB TEXT below"

            else:

                job_embedding = (
                    job.embedding
                )
                embedding_source = "already stored in database"

            details = calculate_match_details(
                resume_embedding=current_user.resume_embedding,
                job_embedding=job_embedding,
                user_skills=current_user.skills or [],
                job_text=job_text,
                resume_text=current_user.resume_text or "",
            )
            confidence_score = float(details["score"])

            _print_matching_debug(
                platform=(job.source or "jobs"),
                job=job,
                details=details,
                embedding_source=embedding_source,
            )

            if (
                confidence_score
                < min_score
            ):
                continue

            ranked_jobs.append({

                "id":
                    str(job.id),

                "title":
                    job.title,

                "company":
                    job.company,

                "location":
                    job.location,

                "salary":
                    job.salary,

                "description":
                    job.description,

                "url":
                    job.url,

                "source":
                    job.source,

                "skill_query":
                    job.skill_query,

                "scraped_at":
                    (
                        job.scraped_at.isoformat()
                        if job.scraped_at
                        else None
                    ),

                "expires_at":
                    (
                        job.expires_at.isoformat()
                        if job.expires_at
                        else None
                    ),

                "confidence_score":
                    confidence_score,

                # Current recommendation list only contains
                # jobs that still need action.
                "application_status":
                    None,

                "applied":
                    False,

            })

        except Exception as exc:

            logger.exception(
                "Semantic matching failed "
                "for job %s: %s",
                job.id,
                exc,
            )

            continue

    if embeddings_updated:

        try:

            await db.commit()

        except Exception:

            await db.rollback()

            logger.exception(
                "Failed saving generated "
                "job embeddings"
            )

    ranked_jobs.sort(

        key=lambda job:
            job[
                "confidence_score"
            ],

        reverse=True,
    )

    total = len(
        ranked_jobs
    )

    paginated_jobs = (
        ranked_jobs[
            skip:
            skip + limit
        ]
    )

    return {

        "total":
            total,

        "skip":
            skip,

        "limit":
            limit,

        "jobs":
            paginated_jobs,

        "matching_method":
            "semantic",

        "excluded_application_jobs":
            len(excluded_job_ids),

        "resume_parsed_at":
            (
                current_user
                .resume_parsed_at
                .isoformat()

                if current_user.resume_parsed_at
                else None
            ),
    }


# =========================================================
# JOB POOL STATUS
# =========================================================

@router.get(
    "/status",
    summary="Global job pool status",
)
async def job_status(

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Information about the GLOBAL job pool.
    """

    now = datetime.utcnow()


    result = await db.execute(

        select(Job).where(
            Job.expires_at > now
        )

    )

    jobs = result.scalars().all()


    total_jobs = len(
        jobs
    )


    counts = {

        "naukri": 0,

        "indeed": 0,

        "internshala": 0,

    }


    jobs_with_embedding = 0


    for job in jobs:

        if job.source in counts:

            counts[
                job.source
            ] += 1


        if job.embedding:

            jobs_with_embedding += 1


    # Most recent scraped job
    result = await db.execute(

        select(Job)

        .order_by(
            desc(Job.scraped_at)
        )

        .limit(1)

    )


    latest_job = (
        result.scalar_one_or_none()
    )


    return {

        "total_active_jobs":
            total_jobs,

        "naukri":
            counts["naukri"],

        "indeed":
            counts["indeed"],

        "internshala":
            counts[
                "internshala"
            ],

        "jobs_with_semantic_embedding":
            jobs_with_embedding,

        "last_scrape_time":
            (
                latest_job
                .scraped_at
                .isoformat()

                if latest_job
                else None
            ),

        "retention_days":
            7,

        "scraping":
            "Handled globally by Celery Beat",

        "matching":
            "SentenceTransformer semantic matching",

    }


# =========================================================
# APPLICATION HISTORY
# =========================================================

@router.get(
    "/applications",
    summary="Get current user's application history",
)
async def get_application_history(

    status: str | None = Query(
        None,
        pattern="^(applied|pending_manual|not_eligible|needs_review|failed)$",
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Return the logged-in user's saved application history.

    pending_manual records contain the original job URL so
    the frontend can show a "Complete Apply" button.
    """

    user_id_str = str(
        current_user.id
    )

    query = (
        select(
            UserApplication,
            Job,
        )
        .join(
            Job,
            UserApplication.job_id
            == Job.id.cast(String),
        )
        .where(
            UserApplication.user_id
            == user_id_str
        )
    )

    if status:

        query = query.where(
            UserApplication.status
            == status
        )

    query = query.order_by(
        UserApplication.updated_at.desc()
    )

    result = await db.execute(
        query
    )

    rows = result.all()

    applications = []

    for application, job in rows:

        applications.append({

            "id":
                application.id,

            "job_id":
                str(job.id),

            "title":
                job.title,

            "company":
                job.company,

            "location":
                job.location,

            "salary":
                job.salary,

            "source":
                job.source,

            "url":
                job.url,

            "status":
                application.status,

            "note":
                application.note,

            "manual_url":
                application.manual_url,

            "created_at":
                (
                    application.created_at.isoformat()
                    if application.created_at
                    else None
                ),

            "updated_at":
                (
                    application.updated_at.isoformat()
                    if application.updated_at
                    else None
                ),

        })

    return {

        "total":
            len(applications),

        "applications":
            applications,

    }


@router.patch(
    "/applications/{job_id}/status",
    summary="Update an application status",
)
async def update_application_status(

    job_id: str,

    status: str = Query(
        ...,
        pattern="^(applied|pending_manual|not_eligible|needs_review|failed)$",
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Useful when the user finishes a pending manual
    application and clicks "Mark as Applied".
    """

    result = await db.execute(

        select(
            UserApplication
        ).where(

            UserApplication.user_id
            == str(current_user.id),

            UserApplication.job_id
            == job_id,

        )
    )

    application = (
        result.scalar_one_or_none()
    )

    if not application:

        raise HTTPException(
            status_code=404,
            detail="Application history entry not found.",
        )

    application.status = status

    application.updated_at = (
        datetime.utcnow()
    )

    if status == "applied":

        application.note = (
            "Application completed."
        )

    elif status == "pending_manual":

        application.note = (
            "Manual action is required to complete this application."
        )

    await db.commit()

    return {

        "message":
            "Application status updated.",

        "job_id":
            job_id,

        "status":
            application.status,

    }


# =========================================================
# APPLICATION HISTORY HELPERS
# =========================================================

def _new_application_id() -> str:
    """
    Generate an ID without requiring any extra package.
    """
    import uuid

    return str(
        uuid.uuid4()
    )


def _normalise_service_results(
    results
) -> list:
    """
    AutoApplyService implementations may return a list of
    dicts, strings, None, etc. Keep the router defensive.
    """

    if results is None:

        return []

    if isinstance(
        results,
        list,
    ):

        return results

    return [
        results
    ]


def _extract_result_job_id(
    item
) -> str | None:

    if not isinstance(
        item,
        dict,
    ):

        return None

    value = (
        item.get("job_id")
        or item.get("id")
        or item.get("jobId")
    )

    if value is None:

        return None

    return str(
        value
    )


def _result_text(
    item
) -> str:

    if isinstance(
        item,
        dict,
    ):

        values = [
            item.get("status"),
            item.get("message"),
            item.get("detail"),
            item.get("reason"),
            item.get("result"),
        ]

        return " ".join(
            str(value)
            for value in values
            if value is not None
        ).lower()

    return str(
        item
    ).lower()


def _classify_auto_apply_result(
    item,
) -> tuple[str | None, str | None]:
    """
    Convert a service result into:
        applied
        pending_manual
        failed

    The explicit successful_job_ids returned by the service
    still take priority over this classifier.
    """

    text = _result_text(
        item
    )

    if not text:

        return (
            None,
            None,
        )

    # Prefer explicit structured status returned by AutoApplyService.
    if isinstance(item, dict):

        explicit_status = str(
            item.get("status")
            or ""
        ).strip().lower()

        explicit_note = (
            item.get("reason")
            or item.get("eligibility_reason")
            or item.get("message")
            or item.get("detail")
        )

        if explicit_status == "not_eligible":

            return (
                "not_eligible",
                str(explicit_note or "User does not meet a hard job requirement."),
            )

        if explicit_status == "needs_review":

            return (
                "needs_review",
                str(explicit_note or "Eligibility could not be confirmed automatically."),
            )

        if explicit_status == "pending_manual":

            return (
                "pending_manual",
                str(explicit_note or "Manual action is required to complete this application."),
            )

        if explicit_status in ("success", "already_applied", "applied"):

            return (
                "applied",
                str(explicit_note or "Applied automatically on Naukri."),
            )

        if explicit_status in ("failed", "error"):

            return (
                "failed",
                str(explicit_note or "Auto-apply failed for this job."),
            )

    manual_markers = [

        "pending_manual",
        "manual required",
        "manual action",
        "complete manually",
        "external apply",
        "external website",
        "company website",
        "redirect",
        "apply on company",
        "apply externally",
        "website opened",
        "opens website",
        "not one click",
        "not one-click",

    ]

    success_markers = [

        "applied successfully",
        "successfully applied",
        "application submitted",
        "application successful",
        "status applied",
        "status: applied",

    ]

    failure_markers = [

        "failed",
        "error",
        "could not apply",
        "unable to apply",
        "login failed",
        "invalid credential",
        "invalid password",

    ]

    if any(
        marker in text
        for marker in manual_markers
    ):

        return (
            "pending_manual",
            "This job requires manual action. Open the job link and complete the application.",
        )

    if any(
        marker in text
        for marker in success_markers
    ):

        return (
            "applied",
            "Applied automatically on Naukri.",
        )

    if any(
        marker in text
        for marker in failure_markers
    ):

        return (
            "failed",
            "Auto-apply failed for this job.",
        )

    return (
        None,
        None,
    )


async def _upsert_application_history(

    db: AsyncSession,

    user_id: str,

    job_id: str,

    status: str,

    note: str | None,

    manual_url: str | None = None,

):
    """
    Create or update one user/job history record.
    """

    result = await db.execute(

        select(
            UserApplication
        ).where(

            UserApplication.user_id
            == user_id,

            UserApplication.job_id
            == job_id,

        )
    )

    application = (
        result.scalar_one_or_none()
    )

    now = datetime.utcnow()

    if application:

        application.status = status

        application.note = note

        application.manual_url = manual_url

        application.updated_at = now

        return application

    application = UserApplication(

        id=_new_application_id(),

        user_id=user_id,

        job_id=job_id,

        status=status,

        note=note,

        manual_url=manual_url,

        created_at=now,

        updated_at=now,

    )

    db.add(
        application
    )

    return application



# =========================================================
# AUTO-APPLY FILTER HELPERS
# =========================================================

def _salary_min_monthly_inr(
    salary_text: str | None,
) -> float | None:
    """
    Convert the LOWER end of a displayed salary range to
    approximate INR/month.

    Conservative behavior:
    - undisclosed/unknown salary -> None
    - 3-5 Lacs P.A. -> 25,000/month lower bound
    - 30,000-40,000 per month -> 30,000/month
    - 3 LPA -> 25,000/month

    If a strict minimum salary filter is active, None is excluded.
    """

    if not salary_text:
        return None

    text = (
        str(salary_text)
        .lower()
        .replace(",", "")
        .replace("₹", " rs ")
    )

    unknown_markers = (
        "not disclosed",
        "undisclosed",
        "not specified",
        "negotiable",
    )

    if any(
        marker in text
        for marker in unknown_markers
    ):
        return None

    numbers = [
        float(value)
        for value in re.findall(
            r"\d+(?:\.\d+)?",
            text,
        )
    ]

    if not numbers:
        return None

    minimum = min(
        numbers[:2]
    )

    is_lakh_annual = bool(
        re.search(
            r"\b(lpa|lac|lacs|lakh|lakhs)\b",
            text,
        )
        or re.search(
            r"per\s*annum|p\.?\s*a\.?|annum",
            text,
        )
    )

    is_monthly = bool(
        re.search(
            r"per\s*month|monthly|/\s*month|/\s*mo\b",
            text,
        )
    )

    if re.search(
        r"\b(crore|crores|cr)\b",
        text,
    ):
        return (
            minimum
            * 10_000_000
            / 12
        )

    if is_lakh_annual:

        # Absolute annual amount such as 300000 PA.
        if minimum >= 10_000:
            return minimum / 12

        return (
            minimum
            * 100_000
            / 12
        )

    if is_monthly:

        has_k = bool(
            re.search(
                r"\d+(?:\.\d+)?\s*k\b",
                text,
            )
        )

        if (
            has_k
            and minimum < 1000
        ):
            return minimum * 1000

        return minimum

    # Raw large absolute figure is most likely annual.
    if minimum >= 100_000:
        return minimum / 12

    return None


def _requested_monthly_salary(
    value: float | None,
    unit: str,
) -> float | None:

    if (
        value is None
        or value <= 0
    ):
        return None

    if unit == "lpa":
        return (
            value
            * 100_000
            / 12
        )

    return value


# =========================================================
# AUTO APPLY
# =========================================================

@router.post(
    "/auto-apply"
)
async def auto_apply_jobs(

    max_applies: int = Query(
        5,
        ge=1,
        le=20,
    ),

    min_salary_value: float | None = Query(
        None,
        ge=0,
    ),

    min_salary_unit: str = Query(
        "lpa",
        pattern="^(lpa|monthly)$",
    ),

    location: str | None = Query(
        None,
    ),

    min_score: float = Query(
        0,
        ge=0,
        le=100,
    ),

    search: str | None = Query(
        None,
    ),

    job_ids: str | None = Query(
        None,
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Auto-apply to top semantic Naukri jobs.

    Applied/pending jobs from this user's history are skipped.

    There is NO minimum semantic threshold:
        semantic score DESC
        -> top max_applies
        -> AutoApplyService

    After the service finishes:
        confirmed eligible + success -> applied
        eligible but external/manual   -> pending_manual
        hard requirement failed        -> not_eligible
        eligibility unclear            -> needs_review
        real error                      -> failed

    If a selected job was not confirmed as successful and the
    service did not report a clear hard failure, it is stored as
    pending_manual so the user can finish it using the saved URL.
    """

    if not current_user.resume_embedding:

        raise HTTPException(
            status_code=400,
            detail=(
                "Upload your resume before "
                "using auto-apply."
            ),
        )

    user_id_str = str(
        current_user.id
    )

    # -----------------------------------------------------
    # Stop previous auto-apply task for same user
    # -----------------------------------------------------

    existing_task = (
        _auto_apply_tasks.get(
            user_id_str
        )
    )

    if (
        existing_task
        and not existing_task.done()
    ):

        existing_task.cancel()

        await asyncio.sleep(
            0.25
        )

    # -----------------------------------------------------
    # Naukri credentials
    # -----------------------------------------------------

    result = await db.execute(

        select(
            PlatformCredential
        ).where(

            PlatformCredential.user_id
            == current_user.id,

            PlatformCredential.platform
            == "naukri",

        )
    )

    credential = (
        result.scalar_one_or_none()
    )

    if not credential:

        raise HTTPException(
            status_code=400,
            detail=(
                "Naukri credentials are not set. "
                "Add them in Profile first."
            ),
        )

    email = credential.email

    password = decrypt_password(
        credential.password_encrypted
    )

    # -----------------------------------------------------
    # Exclude jobs already applied/pending for THIS user
    # -----------------------------------------------------

    history_result = await db.execute(

        select(
            UserApplication.job_id
        ).where(

            UserApplication.user_id
            == user_id_str,

            UserApplication.status.in_(
                [
                    "applied",
                    "pending_manual",
                    "not_eligible",
                    "needs_review",
                ]
            ),
        )
    )

    excluded_job_ids = set(
        history_result.scalars().all()
    )

    # -----------------------------------------------------
    # Get active global Naukri jobs
    # -----------------------------------------------------

    job_query = select(Job).where(

        Job.source
        == "naukri",

        Job.url.isnot(None),

        Job.expires_at
        > datetime.utcnow(),

    )

    if location and location.strip():

        job_query = job_query.where(
            Job.location.ilike(
                f"%{location.strip()}%"
            )
        )

    if search and search.strip():

        search_value = (
            search.strip()
        )

        job_query = job_query.where(

            or_(

                Job.title.ilike(
                    f"%{search_value}%"
                ),

                Job.description.ilike(
                    f"%{search_value}%"
                ),

            )
        )

    # -----------------------------------------------------
    # HARD EXACT-ID GATE
    # -----------------------------------------------------
    # The frontend-visible IDs are the source of truth.  Apply the restriction
    # in SQL itself so unrelated Naukri jobs can never enter this auto-apply
    # request, semantic ranking, eligibility checking, or Selenium.
    requested_job_ids = [
        value.strip()
        for value in (job_ids or "").split(",")
        if value.strip()
    ]

    if requested_job_ids:
        requested_job_ids = requested_job_ids[:max_applies]

        job_query = job_query.where(
            Job.id.cast(String).in_(requested_job_ids)
        )

        logger.warning(
            "[AUTO-APPLY HARD GATE] frontend requested IDs=%s",
            requested_job_ids,
        )

    result = await db.execute(
        job_query
    )

    all_naukri_jobs = (
        result.scalars().all()
    )

    naukri_jobs = [
        job
        for job in all_naukri_jobs
        if str(job.id) not in excluded_job_ids
    ]

    if requested_job_ids:
        by_id = {
            str(job.id): job
            for job in naukri_jobs
        }

        # Preserve exact frontend order.
        naukri_jobs = [
            by_id[job_id]
            for job_id in requested_job_ids
            if job_id in by_id
        ]

        logger.warning(
            "[AUTO-APPLY HARD GATE] DB fetched IDs=%s",
            [str(job.id) for job in naukri_jobs],
        )

        # Fail closed. Never fall back to another job if the requested one
        # disappeared, expired, or was already handled.
        unexpected = [
            str(job.id)
            for job in naukri_jobs
            if str(job.id) not in set(requested_job_ids)
        ]
        if unexpected:
            raise HTTPException(
                status_code=500,
                detail=f"Auto-apply exact-ID guard failed: {unexpected}",
            )

    minimum_monthly_salary = (
        _requested_monthly_salary(
            min_salary_value,
            min_salary_unit,
        )
    )

    if minimum_monthly_salary is not None:

        salary_filtered_jobs = []

        for job in naukri_jobs:

            job_minimum_monthly = (
                _salary_min_monthly_inr(
                    job.salary
                )
            )

            # Strict filter: when salary is unknown, do not
            # auto-apply because the threshold cannot be confirmed.
            if (
                job_minimum_monthly is not None
                and job_minimum_monthly
                >= minimum_monthly_salary
            ):

                salary_filtered_jobs.append(
                    job
                )

        naukri_jobs = (
            salary_filtered_jobs
        )

    if not naukri_jobs:

        return {

            "message":
                "No Naukri jobs match the current auto-apply filters, "
                "or all matching jobs were already handled.",

            "results":
                [],

            "successful":
                0,

            "pending_manual":
                0,

        }

    # -----------------------------------------------------
    # Semantic ranking - no threshold
    # -----------------------------------------------------

    ranked = []

    embeddings_updated = False

    for job in naukri_jobs:

        try:

            job_text = build_job_text(
                job
            )

            if not job.embedding:

                job.embedding = (
                    create_embedding(
                        job_text
                    )
                )

                embeddings_updated = True
                embedding_source = "generated now from EXACT JOB TEXT below"
            else:
                embedding_source = "already stored in database"

            details = calculate_match_details(
                resume_embedding=current_user.resume_embedding,
                job_embedding=job.embedding,
                user_skills=current_user.skills or [],
                job_text=job_text,
                resume_text=current_user.resume_text or "",
            )
            score = float(details["score"])

            _print_matching_debug(
                platform="naukri",
                job=job,
                details=details,
                embedding_source=embedding_source,
            )

            if float(score) < min_score:

                continue

            ranked.append(
                (
                    float(score),
                    job,
                )
            )

        except Exception as exc:

            logger.exception(
                "Semantic matching failed "
                "for Naukri job %s: %s",
                job.id,
                exc,
            )

            continue

    if embeddings_updated:

        try:

            await db.commit()

        except Exception:

            await db.rollback()

            logger.exception(
                "Failed saving generated "
                "Naukri job embeddings"
            )

    if requested_job_ids:
        # Frontend is the source of truth for auto-apply selection/order.
        # Never replace/re-rank the exact visible IDs with another DB job.
        frontend_order = {
            job_id: index
            for index, job_id in enumerate(requested_job_ids)
        }

        ranked.sort(
            key=lambda item: frontend_order.get(
                str(item[1].id),
                len(frontend_order),
            )
        )

        # Frontend already sends the requested visible jobs. Keep the
        # backend bounded to the same requested count.
        ranked = ranked[:max_applies]

        logger.info(
            "[AUTO-APPLY EXACT] final jobs passed to service: %s",
            [
                {
                    "id": str(job.id),
                    "title": job.title,
                }
                for _, job in ranked
            ],
        )
    else:
        # Backward-compatible fallback only if an older client sends no IDs.
        ranked.sort(
            key=lambda item: item[0],
            reverse=True,
        )

    # Pass ranked jobs in order. AutoApplyService performs the eligibility
    # gate and stops after at most max_applies ELIGIBLE attempts. This way
    # an ineligible top-ranked job does not waste an auto-apply slot.
    # If frontend supplied exact visible IDs, keep that exact order.
    # Do NOT let backend semantic re-ranking change which visible job is first.
    if requested_job_ids:
        frontend_order = {
            job_id: index
            for index, job_id in enumerate(requested_job_ids)
        }
        ranked.sort(
            key=lambda pair: frontend_order.get(
                str(pair[1].id),
                len(frontend_order),
            )
        )

        # Frontend already sends at most max_applies IDs. This makes
        # Auto Apply=1 process exactly the first visible job, etc.
        ranked = ranked[:max_applies]

        logger.info(
            "[AUTO-APPLY ORDER] exact frontend order: %s",
            [str(job.id) for _, job in ranked],
        )


    # FINAL SERVICE-BOUNDARY GUARD.
    # Even if future ranking code changes, AutoApplyService can receive only
    # the exact IDs supplied by the frontend.
    if requested_job_ids:
        allowed_ids = set(requested_job_ids)
        ranked = [
            (score, job)
            for score, job in ranked
            if str(job.id) in allowed_ids
        ]

        frontend_order = {
            job_id: index
            for index, job_id in enumerate(requested_job_ids)
        }
        ranked.sort(
            key=lambda pair: frontend_order[str(pair[1].id)]
        )
        ranked = ranked[:max_applies]

    selected = ranked

    logger.warning(
        "[AUTO-APPLY SERVICE GUARD] passing IDs=%s titles=%s",
        [str(job.id) for _, job in selected],
        [job.title for _, job in selected],
    )

    if not selected:

        return {

            "message":
                "No Naukri jobs are currently "
                "available for auto-apply.",

            "results":
                [],

            "successful":
                0,

            "pending_manual":
                0,

        }

    # -----------------------------------------------------
    # User profile for AutoApplyService
    # -----------------------------------------------------

    user_profile = {

        "years_of_experience":
            str(
                current_user
                .years_of_experience
                or 0
            ),

        "current_role":
            (
                current_user.current_role
                or "Software Engineer"
            ),

        "current_company":
            (
                current_user.current_company
                or ""
            ),

        "skills":
            (
                current_user.skills
                or []
            ),

        "highest_education":
            (
                current_user.highest_education
                or ""
            ),

        "full_name":
            current_user.full_name,

        "location":
            (
                current_user.location
                or ""
            ),

    }

    # -----------------------------------------------------
    # Keep enough data for history/frontend
    # -----------------------------------------------------

    jobs_list = [

        {

            "id":
                str(job.id),

            "title":
                job.title,

            "company":
                job.company,

            "location":
                job.location,

            "salary":
                job.salary,

            "url":
                job.url,

            "source":
                job.source,

            "confidence_score":
                score,

            # Eligibility gate needs the actual requirements, not only
            # semantic score/title.
            "description":
                job.description,

            "skill_query":
                job.skill_query,

        }

        for score, job
        in selected
    ]

    selected_job_map = {

        str(job.id): {
            "job": job,
            "score": score,
        }

        for score, job
        in selected
    }

    # -----------------------------------------------------
    # Run existing AutoApplyService
    # -----------------------------------------------------

    from app.services.auto_apply import (
        AutoApplyService,
    )

    async def run_auto_apply():

        def sync_run():

            service = (
                AutoApplyService(

                    email,

                    password,

                    user_profile,

                )
            )

            return service.run_auto_apply(

                jobs_list,

                max_applies,

            )

        loop = (
            asyncio.get_running_loop()
        )

        return await loop.run_in_executor(

            None,

            sync_run,

        )

    task = asyncio.create_task(
        run_auto_apply()
    )

    _auto_apply_tasks[
        user_id_str
    ] = task

    try:

        service_result = await task

        if (
            isinstance(
                service_result,
                tuple,
            )
            and len(
                service_result
            ) == 2
        ):

            results, successful_job_ids = (
                service_result
            )

        else:

            results = service_result

            successful_job_ids = []

    except asyncio.CancelledError:

        return {

            "message":
                "Auto-apply cancelled.",

            "results":
                [],

            "successful":
                0,

            "pending_manual":
                0,

        }

    finally:

        _auto_apply_tasks.pop(
            user_id_str,
            None,
        )

    # -----------------------------------------------------
    # Save application history
    # -----------------------------------------------------

    successful_ids = set(
        str(job_id)
        for job_id in (
            successful_job_ids
            or []
        )
    )

    result_items = (
        _normalise_service_results(
            results
        )
    )

    classified_by_job = {}

    manual_url_by_job = {}

    # First use any explicit per-job service result.
    for item in result_items:

        job_id = (
            _extract_result_job_id(
                item
            )
        )

        if (
            not job_id
            or job_id
            not in selected_job_map
        ):

            continue

        status_value, note = (
            _classify_auto_apply_result(
                item
            )
        )

        if status_value:

            classified_by_job[
                job_id
            ] = (
                status_value,
                note,
            )

            if isinstance(item, dict):
                manual_url_value = item.get("manual_url")
                if manual_url_value:
                    manual_url_by_job[job_id] = str(manual_url_value)

    # successful_job_ids are authoritative.
    for job_id in successful_ids:

        if job_id in selected_job_map:

            classified_by_job[
                job_id
            ] = (
                "applied",
                "Applied automatically on Naukri.",
            )

    # Only jobs explicitly returned by the service were evaluated/attempted.
    # Lower-ranked jobs after the eligible-attempt quota are intentionally
    # untouched and must NOT be recorded as pending.
    returned_job_ids = set()

    for item in result_items:

        result_job_id = _extract_result_job_id(
            item
        )

        if (
            result_job_id
            and result_job_id in selected_job_map
        ):

            returned_job_ids.add(
                result_job_id
            )

    for job_id in successful_ids:

        if job_id in selected_job_map:

            returned_job_ids.add(
                job_id
            )

    # Defensive fallback only for a returned item that somehow had no
    # recognizable status.
    for job_id in returned_job_ids:

        if job_id not in classified_by_job:

            classified_by_job[
                job_id
            ] = (
                "pending_manual",
                (
                    "One-click application was not confirmed. "
                    "Open the job link and complete the application manually."
                ),
            )

    applied_count = 0

    pending_count = 0

    not_eligible_count = 0

    needs_review_count = 0

    failed_count = 0

    for job_id, (
        status_value,
        note,
    ) in classified_by_job.items():

        await _upsert_application_history(

            db=db,

            user_id=user_id_str,

            job_id=job_id,

            status=status_value,

            note=note,

            manual_url=manual_url_by_job.get(
                job_id
            ),

        )

        if status_value == "applied":

            applied_count += 1

        elif status_value == "pending_manual":

            pending_count += 1

        elif status_value == "not_eligible":

            not_eligible_count += 1

        elif status_value == "needs_review":

            needs_review_count += 1

        elif status_value == "failed":

            failed_count += 1

    try:

        await db.commit()

    except Exception:

        await db.rollback()

        logger.exception(
            "Failed saving application history"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Auto-apply ran, but application "
                "history could not be saved."
            ),
        )

    # -----------------------------------------------------
    # Return useful status details to frontend
    # -----------------------------------------------------

    history_results = []

    for job_id, (
        status_value,
        note,
    ) in classified_by_job.items():

        selected_info = (
            selected_job_map[
                job_id
            ]
        )

        job = (
            selected_info[
                "job"
            ]
        )

        history_results.append({

            "job_id":
                job_id,

            "title":
                job.title,

            "company":
                job.company,

            "location":
                job.location,

            "url":
                job.url,

            "manual_url":
                manual_url_by_job.get(
                    job_id
                ),

            "confidence_score":
                selected_info[
                    "score"
                ],

            "status":
                status_value,

            "note":
                note,

        })

    return {

        "message": (
            f"Auto-apply finished. "
            f"Applied: {applied_count}, "
            f"Pending manual: {pending_count}, "
            f"Not eligible: {not_eligible_count}, "
            f"Needs review: {needs_review_count}, "
            f"Failed: {failed_count}."
        ),

        "requested":
            max_applies,

        "selected":
            len(classified_by_job),

        "successful":
            applied_count,

        "pending_manual":
            pending_count,

        "not_eligible":
            not_eligible_count,

        "needs_review":
            needs_review_count,

        "failed":
            failed_count,

        "results":
            history_results,

        "service_results":
            results,

    }



# =========================================================
# INTERNSHALA AUTO APPLY
# =========================================================

@router.post("/auto-apply/internshala")
async def auto_apply_internshala_jobs(
    max_applies: int = Query(5, ge=1, le=20),
    min_salary_value: float | None = Query(None, ge=0),
    min_salary_unit: str = Query("monthly", pattern="^(lpa|monthly)$"),
    location: str | None = Query(None),
    min_score: float = Query(0, ge=0, le=100),
    search: str | None = Query(None),
    job_ids: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Filters -> semantic ranking -> eligibility -> Internshala auto-apply.
    Unknown questions/CAPTCHA/OTP become pending_manual.
    """

    if not current_user.resume_embedding:
        raise HTTPException(
            status_code=400,
            detail="Upload your resume before using Internshala auto-apply.",
        )

    user_id_str = str(current_user.id)

    # Do not run two browser auto-apply jobs for one user simultaneously.
    existing_task = _auto_apply_tasks.get(user_id_str)
    if existing_task and not existing_task.done():
        existing_task.cancel()
        await asyncio.sleep(0.25)

    # Saved Internshala credentials.
    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "internshala",
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=400,
            detail=(
                "Internshala credentials are not set. "
                "Save Internshala email/password first."
            ),
        )

    email = credential.email
    password = decrypt_password(credential.password_encrypted)

    # Skip jobs already dispositioned for this user.
    history_result = await db.execute(
        select(UserApplication.job_id).where(
            UserApplication.user_id == user_id_str,
            UserApplication.status.in_([
                "applied",
                "pending_manual",
                "not_eligible",
                "needs_review",
            ]),
        )
    )
    excluded_job_ids = set(history_result.scalars().all())

    query = select(Job).where(
        Job.source == "internshala",
        Job.url.isnot(None),
        Job.expires_at > datetime.utcnow(),
    )

    if location and location.strip():
        query = query.where(
            Job.location.ilike(f"%{location.strip()}%")
        )

    if search and search.strip():
        s = search.strip()
        query = query.where(
            or_(
                Job.title.ilike(f"%{s}%"),
                Job.description.ilike(f"%{s}%"),
            )
        )

    result = await db.execute(query)
    jobs = [
        job
        for job in result.scalars().all()
        if str(job.id) not in excluded_job_ids
    ]

    # If the frontend supplies its currently visible filtered Internshala jobs,
    # never auto-apply outside that exact visible candidate set.
    requested_job_ids = []
    if job_ids:
        requested_job_ids = [
            value.strip()
            for value in job_ids.split(",")
            if value.strip()
        ]
        allowed_ids = set(requested_job_ids)
        jobs = [job for job in jobs if str(job.id) in allowed_ids]

    # Strict salary filter.
    requested_monthly = _requested_monthly_salary(
        min_salary_value,
        min_salary_unit,
    )

    if requested_monthly is not None:
        jobs = [
            job
            for job in jobs
            if (
                _salary_min_monthly_inr(job.salary) is not None
                and _salary_min_monthly_inr(job.salary) >= requested_monthly
            )
        ]

    if not jobs:
        return {
            "message": "No Internshala jobs match the current filters.",
            "results": [],
            "successful": 0,
            "pending_manual": 0,
            "not_eligible": 0,
            "needs_review": 0,
            "failed": 0,
        }

    ranked = []
    embeddings_updated = False

    for job in jobs:
        try:
            job_text = build_job_text(job)

            if not job.embedding:
                job.embedding = create_embedding(job_text)
                embeddings_updated = True
                embedding_source = "generated now from EXACT JOB TEXT below"
            else:
                embedding_source = "already stored in database"

            details = calculate_match_details(
                resume_embedding=current_user.resume_embedding,
                job_embedding=job.embedding,
                user_skills=current_user.skills or [],
                job_text=job_text,
                resume_text=current_user.resume_text or "",
            )
            score = float(details["score"])

            _print_matching_debug(
                platform="internshala",
                job=job,
                details=details,
                embedding_source=embedding_source,
            )

            if score >= min_score:
                ranked.append((score, job))

        except Exception as exc:
            logger.exception(
                "Internshala semantic matching failed for %s: %s",
                job.id,
                exc,
            )

    if embeddings_updated:
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    ranked.sort(key=lambda x: x[0], reverse=True)

    # Number of Jobs means the TOP N filtered/ranked jobs shown to the user.
    # Eligibility is evaluated only inside this top-N set; the service must not
    # walk down into unrelated lower-ranked jobs to fill the quota.
    ranked = ranked[:max_applies]

    if not ranked:
        return {
            "message": "No Internshala jobs meet the current match/filter criteria.",
            "results": [],
            "successful": 0,
            "pending_manual": 0,
            "not_eligible": 0,
            "needs_review": 0,
            "failed": 0,
        }

    user_profile = {
        "years_of_experience": str(current_user.years_of_experience or 0),
        "current_role": current_user.current_role or "",
        "current_company": current_user.current_company or "",
        "skills": current_user.skills or [],
        "highest_education": current_user.highest_education or "",
        "full_name": current_user.full_name,
        "location": current_user.location or "",
    }

    jobs_list = [
        {
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary": job.salary,
            "url": job.url,
            "source": job.source,
            "confidence_score": score,
            "description": job.description,
            "skill_query": job.skill_query,
        }
        for score, job in ranked
    ]

    ranked_map = {
        str(job.id): {"job": job, "score": score}
        for score, job in ranked
    }

    from app.services.internshala_auto_apply import InternshalaAutoApplyService

    async def run_service():
        def sync_run():
            service = InternshalaAutoApplyService(
                email=email,
                password=password,
                user_profile=user_profile,
            )
            return service.run_auto_apply(
                jobs_list,
                max_applies,
            )

        return await asyncio.get_running_loop().run_in_executor(
            None,
            sync_run,
        )

    task = asyncio.create_task(run_service())
    _auto_apply_tasks[user_id_str] = task

    try:
        service_result = await task
        if isinstance(service_result, tuple) and len(service_result) == 2:
            results, successful_job_ids = service_result
        else:
            results = service_result or []
            successful_job_ids = []
    except asyncio.CancelledError:
        return {
            "message": "Internshala auto-apply cancelled.",
            "results": [],
            "successful": 0,
        }
    finally:
        _auto_apply_tasks.pop(user_id_str, None)

    applied_count = 0
    pending_count = 0
    not_eligible_count = 0
    needs_review_count = 0
    failed_count = 0
    response_results = []

    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue

        job_id = str(item.get("job_id") or "")
        if not job_id or job_id not in ranked_map:
            continue

        raw_status = str(item.get("status") or "").lower().strip()

        if raw_status in ("success", "already_applied", "applied"):
            status_value = "applied"
        elif raw_status in (
            "pending_manual",
            "not_eligible",
            "needs_review",
            "failed",
        ):
            status_value = raw_status
        else:
            status_value = "pending_manual"

        note = str(
            item.get("message")
            or item.get("reason")
            or "Internshala application requires manual review."
        )
        manual_url = item.get("manual_url")

        await _upsert_application_history(
            db=db,
            user_id=user_id_str,
            job_id=job_id,
            status=status_value,
            note=note,
            manual_url=str(manual_url) if manual_url else None,
        )

        if status_value == "applied":
            applied_count += 1
        elif status_value == "pending_manual":
            pending_count += 1
        elif status_value == "not_eligible":
            not_eligible_count += 1
        elif status_value == "needs_review":
            needs_review_count += 1
        elif status_value == "failed":
            failed_count += 1

        info = ranked_map[job_id]
        job = info["job"]

        response_results.append({
            "job_id": job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "manual_url": manual_url,
            "confidence_score": info["score"],
            "status": status_value,
            "note": note,
            "source": "internshala",
        })

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=(
                "Internshala auto-apply ran, "
                "but application history could not be saved."
            ),
        )

    return {
        "message": (
            f"Internshala auto-apply finished. "
            f"Applied: {applied_count}, "
            f"Pending manual: {pending_count}, "
            f"Not eligible: {not_eligible_count}, "
            f"Needs review: {needs_review_count}, "
            f"Failed: {failed_count}."
        ),
        "requested": max_applies,
        "successful": applied_count,
        "pending_manual": pending_count,
        "not_eligible": not_eligible_count,
        "needs_review": needs_review_count,
        "failed": failed_count,
        "results": response_results,
    }


# =========================================================
# CANCEL AUTO APPLY
# =========================================================

@router.post(
    "/auto-apply/cancel"
)
async def cancel_auto_apply(

    current_user: User = Depends(
        get_current_user
    ),
):

    user_id = str(
        current_user.id
    )


    task = (
        _auto_apply_tasks.get(
            user_id
        )
    )


    if (
        task
        and not task.done()
    ):

        task.cancel()


        return {

            "message":
                "Auto-apply cancellation requested."

        }


    return {

        "message":
            "No auto-apply task is currently running."

    }