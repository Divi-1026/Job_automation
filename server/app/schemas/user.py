from __future__ import annotations
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import ExperienceType


# ── Request Schemas ──────────────────────────────────────────────────────────

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

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Response Schemas ─────────────────────────────────────────────────────────

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
    resume_url: Optional[str] = None
    experience_type: ExperienceType
    years_of_experience: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    highest_education: Optional[str] = None
    college: Optional[str] = None
    graduation_year: Optional[int] = None
    skills: List[str] = []
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, v):
        """PostgreSQL ARRAY can come back as None for older rows — default to []."""
        return v if v is not None else []


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Profile Update Schema (all fields optional — PATCH semantics) ─────────────
# full_name and email are intentionally excluded — contact support to change those.

class ProfileUpdate(BaseModel):
    phone: Optional[str] = None
    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    experience_type: Optional[ExperienceType] = None
    years_of_experience: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    highest_education: Optional[str] = None
    college: Optional[str] = None
    graduation_year: Optional[int] = None
    skills: Optional[List[str]] = None
    resume_url: Optional[str] = None


# ── Password Change Schema ────────────────────────────────────────────────────

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


# ── Email Change Schema ───────────────────────────────────────────────────────

class EmailChange(BaseModel):
    new_email: EmailStr
    password: str  # require current password to confirm email change
