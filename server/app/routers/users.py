import uuid as _uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    OAuth2PasswordBearer,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.core.security import (
    decode_access_token,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login/form"
)


async def get_current_user(
    token: str = Depends(
        oauth2_scheme
    ),

    db: AsyncSession = Depends(
        get_db
    ),
) -> User:

    payload = decode_access_token(
        token
    )

    if not payload:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid or expired token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    try:
        user_id = _uuid.UUID(
            payload["sub"]
        )

    except (
        ValueError,
        KeyError,
        TypeError,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid token payload.",
        )


    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()


    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="User not found.",
        )


    if not user.is_active:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="Account is inactive.",
        )


    return user


@router.get(
    "/me",
    response_model=UserOut,
)
async def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user