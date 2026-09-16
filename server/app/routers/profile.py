import os
import uuid
import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select,
    update as sql_update,
)

from app.database import get_db
from app.models.user import User

from app.schemas.user import (
    UserOut,
    ProfileUpdate,
    PasswordChange,
    EmailChange,
)

from app.core.security import (
    hash_password,
    verify_password,
)

from app.routers.users import (
    get_current_user,
)


logger = logging.getLogger(__name__)


UPLOAD_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "uploads",
        "resumes",
    )
)

MAX_FILE_SIZE = 10 * 1024 * 1024


router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


# ---------------------------------------------------------
# GET PROFILE
# ---------------------------------------------------------

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get my profile",
)
async def get_profile(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user


# ---------------------------------------------------------
# UPDATE PROFILE
# ---------------------------------------------------------

@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update my profile",
)
async def update_profile(
    body: ProfileUpdate,

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(
        include=body.model_fields_set
    )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update.",
        )

    # Resume fields must not be manually overwritten
    # through the normal profile endpoint.
    protected_fields = {
        "resume_filename",
        "resume_url",
        "resume_text",
        "resume_embedding",
        "resume_parsed_at",
    }

    for field in protected_fields:
        update_data.pop(
            field,
            None,
        )

    await db.execute(
        sql_update(User)
        .where(
            User.id
            == current_user.id
        )
        .values(**update_data)
    )

    await db.flush()

    await db.refresh(
        current_user
    )

    return current_user


# ---------------------------------------------------------
# CHANGE PASSWORD
# ---------------------------------------------------------

@router.post(
    "/me/password",
    status_code=status.HTTP_200_OK,
)
async def change_password(
    body: PasswordChange,

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    if not verify_password(
        body.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect.",
        )

    if (
        body.current_password
        == body.new_password
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "New password must be different "
                "from the current password."
            ),
        )

    current_user.hashed_password = (
        hash_password(
            body.new_password
        )
    )

    db.add(current_user)

    await db.flush()

    return {
        "message":
            "Password updated successfully."
    }


# ---------------------------------------------------------
# CHANGE EMAIL
# ---------------------------------------------------------

@router.post(
    "/me/email",
    response_model=UserOut,
)
async def change_email(
    body: EmailChange,

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    if not verify_password(
        body.password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Password is incorrect.",
        )

    email = (
        body.new_email
        .strip()
        .lower()
    )

    result = await db.execute(
        select(User).where(
            User.email == email,
            User.id != current_user.id,
        )
    )

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=(
                "This email is already in use."
            ),
        )

    current_user.email = email

    db.add(current_user)

    await db.flush()

    await db.refresh(
        current_user
    )

    return current_user


# ---------------------------------------------------------
# RESUME UPLOAD
#
# THIS is where resume parsing happens.
#
# It is NOT parsed again in GET /jobs.
# ---------------------------------------------------------

@router.post(
    "/me/resume",
    response_model=UserOut,
    summary="Upload or replace resume",
)
async def upload_resume(
    file: UploadFile = File(...),

    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in {
        "application/pdf",
        "application/x-pdf",
    }:
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=(
                "File too large. Maximum size "
                "is 10 MB."
            ),
        )

    # ---------------------------------------------
    # Parse resume before replacing old file.
    # If parsing fails, user's previous resume
    # remains untouched.
    # ---------------------------------------------

    from app.utils.resume_processor import (
        extract_text_from_pdf,
        extract_skills_from_text,
        merge_skills,
    )

    from app.utils.semantic_match import (
        create_embedding,
    )

    try:
        resume_text = (
            extract_text_from_pdf(
                content
            )
        )

    except Exception as exc:
        logger.exception(
            "Resume text extraction failed"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not read text from this PDF."
            ),
        ) from exc


    if not resume_text or not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text found in resume."
            ),
        )


    # ---------------------------------------------
    # Extract skills
    # ---------------------------------------------

    try:
        extracted_skills = (
            extract_skills_from_text(
                resume_text
            )
            or []
        )

    except Exception:
        logger.exception(
            "Resume skill extraction failed"
        )

        extracted_skills = []


    # ---------------------------------------------
    # Generate semantic embedding ONCE
    # ---------------------------------------------

    try:
        resume_embedding = (
            create_embedding(
                resume_text
            )
        )

    except Exception as exc:
        logger.exception(
            "Resume embedding generation failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not generate resume embedding."
            ),
        ) from exc


    # create_embedding may return numpy array
    if hasattr(
        resume_embedding,
        "tolist",
    ):
        resume_embedding = (
            resume_embedding.tolist()
        )


    # ---------------------------------------------
    # Store physical PDF
    # ---------------------------------------------

    os.makedirs(
        UPLOAD_DIR,
        exist_ok=True,
    )

    new_filename = (
        f"{uuid.uuid4()}.pdf"
    )

    new_path = os.path.join(
        UPLOAD_DIR,
        new_filename,
    )


    try:
        with open(
            new_path,
            "wb",
        ) as output_file:
            output_file.write(content)

    except OSError as exc:
        logger.exception(
            "Could not save resume"
        )

        raise HTTPException(
            status_code=500,
            detail="Could not save resume.",
        ) from exc


    # ---------------------------------------------
    # Delete previous file only after new one works
    # ---------------------------------------------

    if current_user.resume_url:
        old_filename = os.path.basename(
            current_user.resume_url
        )

        old_path = os.path.join(
            UPLOAD_DIR,
            old_filename,
        )

        if (
            os.path.isfile(old_path)
            and old_path != new_path
        ):
            try:
                os.remove(old_path)
            except OSError:
                logger.warning(
                    "Could not delete old resume: %s",
                    old_path,
                )


    # ---------------------------------------------
    # Merge extracted skills
    # ---------------------------------------------

    # Resume replacement must not accumulate stale skills from an older resume.
    # The resume is the source of truth for automatically extracted matching skills.
    merged_skills = merge_skills(
        [],
        extracted_skills,
    )


    # ---------------------------------------------
    # SAVE parsed resume ONCE
    # ---------------------------------------------

    current_user.resume_filename = (
        file.filename
        or new_filename
    )

    current_user.resume_url = (
        f"/uploads/resumes/{new_filename}"
    )

    current_user.resume_text = (
        resume_text
    )

    current_user.resume_embedding = (
        resume_embedding
    )

    current_user.resume_parsed_at = (
        datetime.now(timezone.utc)
    )

    current_user.skills = (
        merged_skills
    )

    db.add(current_user)

    await db.flush()

    await db.refresh(
        current_user
    )

    logger.info(
        "Resume parsed and saved for user %s",
        current_user.id,
    )

    return current_user


# ---------------------------------------------------------
# DELETE RESUME
# ---------------------------------------------------------

@router.delete(
    "/me/resume",
    response_model=UserOut,
    summary="Remove resume",
)
async def delete_resume(
    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    if not current_user.resume_url:
        raise HTTPException(
            status_code=404,
            detail=(
                "No resume found on this account."
            ),
        )


    old_filename = os.path.basename(
        current_user.resume_url
    )

    old_path = os.path.join(
        UPLOAD_DIR,
        old_filename,
    )


    if os.path.isfile(old_path):
        try:
            os.remove(old_path)

        except OSError:
            logger.exception(
                "Failed to delete resume file"
            )


    current_user.resume_filename = None
    current_user.resume_url = None
    current_user.resume_text = None
    current_user.resume_embedding = None
    current_user.resume_parsed_at = None


    db.add(current_user)

    await db.flush()

    await db.refresh(
        current_user
    )

    return current_user


# ---------------------------------------------------------
# DEACTIVATE ACCOUNT
# ---------------------------------------------------------

@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
)
async def deactivate_account(
    current_user: User = Depends(
        get_current_user
    ),

    db: AsyncSession = Depends(get_db),
):
    current_user.is_active = False

    db.add(current_user)

    await db.flush()

    return {
        "message":
            "Account deactivated successfully."
    }