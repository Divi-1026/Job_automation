"""
CareerSync platform credentials router.

Supported:
- GET  /credentials/naukri
- POST /credentials/naukri
- GET  /credentials/internshala
- POST /credentials/internshala

Passwords are encrypted before storage and are never returned by GET endpoints.
"""

import os

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.platform_credential import PlatformCredential
from app.models.user import User
from app.routers.users import get_current_user


router = APIRouter(
    prefix="/credentials",
    tags=["Platform Credentials"],
)


class CredentialSaveRequest(BaseModel):
    platform: str | None = None
    email: EmailStr
    password: str


def _encrypt_password(password: str) -> str:
    """
    Use app.utils.encryption.encrypt_password when available.
    Fallback uses the same FERNET_KEY directly.
    """
    try:
        from app.utils.encryption import encrypt_password
        return encrypt_password(password)
    except (ImportError, AttributeError):
        key = os.getenv("FERNET_KEY")

        if not key:
            raise HTTPException(
                status_code=500,
                detail="FERNET_KEY is not configured on the server.",
            )

        try:
            return (
                Fernet(key.encode() if isinstance(key, str) else key)
                .encrypt(password.encode())
                .decode()
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Could not encrypt platform credentials.",
            ) from exc


async def _get_credential(
    platform: str,
    current_user: User,
    db: AsyncSession,
):
    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == platform,
        )
    )

    credential = result.scalar_one_or_none()

    if not credential:
        return {
            "exists": False,
            "platform": platform,
            "email": None,
        }

    return {
        "exists": True,
        "platform": platform,
        "email": credential.email,
    }


async def _save_credential(
    platform: str,
    body: CredentialSaveRequest,
    current_user: User,
    db: AsyncSession,
):
    email = str(body.email).strip()
    password = body.password

    if not password:
        raise HTTPException(
            status_code=400,
            detail=f"{platform.title()} password is required.",
        )

    if body.platform and body.platform.lower().strip() != platform:
        raise HTTPException(
            status_code=400,
            detail="Credential platform does not match the endpoint.",
        )

    encrypted_password = _encrypt_password(password)

    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == platform,
        )
    )

    credential = result.scalar_one_or_none()

    if credential:
        credential.email = email
        credential.password_encrypted = encrypted_password
    else:
        credential = PlatformCredential(
            user_id=current_user.id,
            platform=platform,
            email=email,
            password_encrypted=encrypted_password,
        )
        db.add(credential)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not save {platform.title()} credentials.",
        ) from exc

    return {
        "success": True,
        "exists": True,
        "platform": platform,
        "email": email,
        "message": f"{platform.title()} credentials saved successfully.",
    }


@router.get("/naukri")
async def get_naukri_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_credential(
        platform="naukri",
        current_user=current_user,
        db=db,
    )


@router.post("/naukri")
async def save_naukri_credentials(
    body: CredentialSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _save_credential(
        platform="naukri",
        body=body,
        current_user=current_user,
        db=db,
    )


@router.get("/internshala")
async def get_internshala_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_credential(
        platform="internshala",
        current_user=current_user,
        db=db,
    )


@router.post("/internshala")
async def save_internshala_credentials(
    body: CredentialSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _save_credential(
        platform="internshala",
        body=body,
        current_user=current_user,
        db=db,
    )
