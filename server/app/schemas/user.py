from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
)

from app.models.user import ExperienceType


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    phone: Optional[str] = None

    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    portfolio_url: Optional[str] = None

    location: Optional[str] = None
    bio: Optional[str] = None

    experience_type: ExperienceType = ExperienceType.fresher
    years_of_experience: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None

    highest_education: Optional[str] = None
    college: Optional[str] = None
    graduation_year: Optional[int] = None

    skills: List[str] = []
    preferred_roles: List[str] = []

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError(
                "Password must be at least 8 characters"
            )

        return value

    @field_validator(
        "skills",
        "preferred_roles",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value):
        if value is None:
            return []

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# =========================================================
# RESPONSE SCHEMAS
# =========================================================

class UserOut(BaseModel):
    id: UUID

    full_name: str
    email: EmailStr

    phone: Optional[str] = None

    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    portfolio_url: Optional[str] = None

    location: Optional[str] = None
    bio: Optional[str] = None

    # -----------------------------------------------------
    # Resume
    # -----------------------------------------------------

    resume_filename: Optional[str] = None

    resume_url: Optional[str] = None

    resume_parsed_at: Optional[datetime] = None

    # Useful for frontend:
    # user.has_resume
    has_resume: bool = False

    # -----------------------------------------------------
    # Experience
    # -----------------------------------------------------

    experience_type: ExperienceType

    years_of_experience: Optional[int] = None

    current_company: Optional[str] = None
    current_role: Optional[str] = None

    # -----------------------------------------------------
    # Education
    # -----------------------------------------------------

    highest_education: Optional[str] = None
    college: Optional[str] = None
    graduation_year: Optional[int] = None

    # -----------------------------------------------------
    # Skills / preferences
    # -----------------------------------------------------

    skills: List[str] = []

    preferred_roles: List[str] = []

    # -----------------------------------------------------
    # Account metadata
    # -----------------------------------------------------

    is_active: bool

    created_at: datetime

    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


    @field_validator(
        "skills",
        "preferred_roles",
        mode="before",
    )
    @classmethod
    def coerce_arrays(cls, value):
        """
        PostgreSQL ARRAY may be NULL for older users.
        Return [] instead.
        """

        return (
            value
            if value is not None
            else []
        )


    @classmethod
    def model_validate(
        cls,
        obj,
        *args,
        **kwargs,
    ):
        """
        Add derived has_resume field while converting
        SQLAlchemy User -> Pydantic UserOut.
        """

        instance = super().model_validate(
            obj,
            *args,
            **kwargs,
        )

        instance.has_resume = bool(
            getattr(
                obj,
                "resume_text",
                None,
            )
            and getattr(
                obj,
                "resume_embedding",
                None,
            )
        )

        return instance


class TokenOut(BaseModel):
    access_token: str

    token_type: str = "bearer"

    user: UserOut


# =========================================================
# PROFILE UPDATE
# =========================================================

class ProfileUpdate(BaseModel):
    phone: Optional[str] = None

    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    portfolio_url: Optional[str] = None

    location: Optional[str] = None
    bio: Optional[str] = None

    experience_type: Optional[
        ExperienceType
    ] = None

    years_of_experience: Optional[int] = None

    current_company: Optional[str] = None

    current_role: Optional[str] = None

    highest_education: Optional[str] = None

    college: Optional[str] = None

    graduation_year: Optional[int] = None

    skills: Optional[
        List[str]
    ] = None

    preferred_roles: Optional[
        List[str]
    ] = None

    # IMPORTANT:
    # resume_url / resume_text / resume_embedding
    # are intentionally NOT editable here.
    #
    # Resume must only change through:
    # POST /profile/me/resume


    @field_validator(
        "skills",
        "preferred_roles",
        mode="before",
    )
    @classmethod
    def normalize_optional_lists(
        cls,
        value,
    ):
        if value is None:
            return None

        return value


# =========================================================
# PASSWORD CHANGE
# =========================================================

class PasswordChange(BaseModel):
    current_password: str

    new_password: str

    @field_validator(
        "new_password"
    )
    @classmethod
    def password_strength(
        cls,
        value: str,
    ) -> str:

        if len(value) < 8:

            raise ValueError(
                "New password must be at least 8 characters"
            )

        return value


# =========================================================
# EMAIL CHANGE
# =========================================================

class EmailChange(BaseModel):
    new_email: EmailStr

    password: str