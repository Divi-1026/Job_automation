from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserSignup, UserOut, TokenOut, UserLogin
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.routers.users import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/signup",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: UserSignup,
    db: AsyncSession = Depends(get_db),
):
    email = payload.email.strip().lower()

    result = await db.execute(
        select(User).where(User.email == email)
    )

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        full_name=payload.full_name,
        email=email,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        github_id=payload.github_id,
        linkedin_id=payload.linkedin_id,
        portfolio_url=payload.portfolio_url,
        location=payload.location,
        bio=payload.bio,
        experience_type=payload.experience_type,
        years_of_experience=payload.years_of_experience,
        current_company=payload.current_company,
        current_role=payload.current_role,
        highest_education=payload.highest_education,
        college=payload.college,
        graduation_year=payload.graduation_year,
        skills=payload.skills or [],
        preferred_roles=getattr(
            payload,
            "preferred_roles",
            [],
        ) or [],
    )

    db.add(user)

    await db.flush()
    await db.refresh(user)

    token = create_access_token({
        "sub": str(user.id)
    })

    return TokenOut(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenOut,
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    email = payload.email.strip().lower()

    result = await db.execute(
        select(User).where(
            User.email == email
        )
    )

    user = result.scalar_one_or_none()

    if (
        not user
        or not verify_password(
            payload.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    token = create_access_token({
        "sub": str(user.id)
    })

    return TokenOut(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout_user(
    current_user: User = Depends(
        get_current_user
    ),
):
    return {
        "message": "Logged out successfully."
    }


@router.post(
    "/login/form",
    response_model=TokenOut,
    include_in_schema=False,
)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.email
            == form.username.strip().lower()
        )
    )

    user = result.scalar_one_or_none()

    if (
        not user
        or not verify_password(
            form.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    token = create_access_token({
        "sub": str(user.id)
    })

    return TokenOut(
        access_token=token,
        user=UserOut.model_validate(user),
    )