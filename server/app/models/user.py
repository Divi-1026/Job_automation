import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, Enum as PgEnum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from app.database import Base
import enum


class ExperienceType(str, enum.Enum):
    fresher = "fresher"
    experienced = "experienced"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    full_name      = Column(String(150), nullable=False)
    email          = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    phone          = Column(String(15), nullable=True)

    # Social / portfolio links
    github_id      = Column(String(100), nullable=True)
    linkedin_id    = Column(String(100), nullable=True)
    portfolio_url  = Column(String(255), nullable=True)
    location       = Column(String(150), nullable=True)
    bio            = Column(Text, nullable=True)
    resume_url     = Column(String(500), nullable=True)   # stored path / S3 URL

    # Experience
    experience_type    = Column(PgEnum(ExperienceType), default=ExperienceType.fresher, nullable=False)
    years_of_experience = Column(Integer, nullable=True)
    current_company    = Column(String(150), nullable=True)
    current_role       = Column(String(150), nullable=True)

    # Education
    highest_education  = Column(String(100), nullable=True)
    college            = Column(String(200), nullable=True)
    graduation_year    = Column(Integer, nullable=True)

    # Skills stored as a PostgreSQL text array
    skills = Column(ARRAY(String), nullable=True, default=list)

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
