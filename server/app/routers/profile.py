"""
Profile router — all CRUD operations a user can perform on their own account.

Endpoints
─────────
GET    /profile/me            → fetch full profile
PATCH  /profile/me            → update any profile fields (partial update)
POST   /profile/me/password   → change password (requires current password)
POST   /profile/me/email      → change email (requires current password)
POST   /profile/me/resume     → upload / replace resume PDF (returns updated profile)
DELETE /profile/me/resume     → remove resume file and clear resume_url
DELETE /profile/me            → soft-delete / deactivate account
"""

import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut, ProfileUpdate, PasswordChange, EmailChange
from app.core.security import hash_password, verify_password
from app.routers.users import get_current_user

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "resumes")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/profile", tags=["Profile"])

# ── GET /profile/me ──────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut, summary="Get my profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Return the full profile of the authenticated user."""
    return current_user


# ── PATCH /profile/me ────────────────────────────────────────────────────────
@router.patch("/me", response_model=UserOut, summary="Update my profile")
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Partial update — only fields present in the request body are changed.
    Any field set to null in the body will clear that column.
    """
    # model_fields_set contains only the keys the caller explicitly sent
    update_data = body.model_dump(include=body.model_fields_set)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    # Use a direct SQL UPDATE to bypass SQLAlchemy's ORM change-tracking,
    # which is unreliable for PostgreSQL ARRAY columns (skills).
    await db.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(**update_data)
    )
    await db.refresh(current_user)


    return current_user


# ── POST /profile/me/password ─────────────────────────────────────────────────
@router.post("/me/password", status_code=status.HTTP_200_OK, summary="Change password")
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password after verifying the current one."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    await db.flush()
    return {"message": "Password updated successfully."}


# ── POST /profile/me/email ───────────────────────────────────────────────────
@router.post("/me/email", response_model=UserOut, summary="Change email")
async def change_email(
    body: EmailChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change email address after verifying the current password."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect.",
        )

    # Make sure the new email is not taken by another account
    result = await db.execute(
        select(User).where(User.email == body.new_email, User.id != current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already in use by another account.",
        )

    current_user.email = body.new_email
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user


# ── DELETE /profile/me ────────────────────────────────────────────────────────
@router.delete("/me", status_code=status.HTTP_200_OK, summary="Deactivate my account")
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete: marks the account as inactive so the user cannot log in again.
    Data is retained for 30 days before hard-deletion (implement a background job).
    """
    current_user.is_active = False
    db.add(current_user)
    await db.flush()
    return {"message": "Account deactivated. You have been signed out."}


@router.post("/me/resume", response_model=UserOut, summary="Upload or replace resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a new resume PDF.
    - Saves the file.
    - Extracts text and uses Gemini API to get technical skills.
    - Merges new skills with existing user skills and updates DB.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    # 1. Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if current_user.resume_url:
        old_filename = current_user.resume_url.lstrip("/").replace("uploads/resumes/", "")
        old_path = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.isfile(old_path):
            os.remove(old_path)

    filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 2. Extract skills from resume
    from app.utils.resume_processor import extract_text_from_pdf, extract_skills_from_text, merge_skills

    try:
        resume_text = extract_text_from_pdf(content)
        if resume_text:
            new_skills = extract_skills_from_text(resume_text)
            if new_skills:
                current_skills = current_user.skills or []
                merged = merge_skills(current_skills, new_skills)
                current_user.skills = merged
                logger.info(f"Added {len(new_skills)} skills from resume for user {current_user.id}")
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}", exc_info=True)
        # Do not fail the whole request – just log and continue

    # 3. Update resume_url
    current_user.resume_url = f"/uploads/resumes/{filename}"
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user

# ── DELETE /profile/me/resume ─────────────────────────────────────────────────
@router.delete("/me/resume", response_model=UserOut, summary="Remove resume")
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the resume file from disk and clear resume_url on the profile.
    """
    if not current_user.resume_url:
        raise HTTPException(status_code=404, detail="No resume found on this account.")

    old_filename = current_user.resume_url.lstrip("/").replace("uploads/resumes/", "")
    old_path = os.path.join(UPLOAD_DIR, old_filename)
    if os.path.isfile(old_path):
        os.remove(old_path)

    current_user.resume_url = None
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user
