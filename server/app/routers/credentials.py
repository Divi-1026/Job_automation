from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.platform_credential import PlatformCredential
from app.routers.users import get_current_user
from app.utils.encryption import encrypt_password, decrypt_password

router = APIRouter(prefix="/credentials", tags=["Credentials"])

class CredentialsRequest(BaseModel):
    platform: str
    email: str
    password: str

@router.post("/naukri")
async def save_naukri_credentials(
    cred: CredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if cred.platform != "naukri":
        raise HTTPException(400, "Only 'naukri' platform supported")
    
    # Check existing
    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "naukri"
        )
    )
    existing = result.scalar_one_or_none()
    
    encrypted = encrypt_password(cred.password)
    if existing:
        existing.email = cred.email
        existing.password_encrypted = encrypted
    else:
        new_cred = PlatformCredential(
            user_id=current_user.id,
            platform="naukri",
            email=cred.email,
            password_encrypted=encrypted
        )
        db.add(new_cred)
    await db.commit()
    return {"message": "Credentials saved successfully"}

@router.get("/naukri")
async def get_naukri_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlatformCredential).where(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "naukri"
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return {"exists": False}
    # Never return password; just email
    return {"exists": True, "email": cred.email}