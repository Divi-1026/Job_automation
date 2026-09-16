import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    Enum as PgEnum,
    Float,
)
from sqlalchemy.dialects.postgresql import (
    UUID,
    ARRAY,
)
from sqlalchemy.sql import func

from app.database import Base


class ExperienceType(
    str,
    enum.Enum,
):
    fresher = "fresher"
    experienced = "experienced"


class User(Base):
    __tablename__ = "users"

    # -----------------------------------------------------
    # Authentication
    # -----------------------------------------------------

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    full_name = Column(
        String(150),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password = Column(
        String,
        nullable=False,
    )

    phone = Column(
        String(20),
        nullable=True,
    )

    # -----------------------------------------------------
    # Candidate profile
    # -----------------------------------------------------

    github_id = Column(
        String(255),
        nullable=True,
    )

    linkedin_id = Column(
        String(255),
        nullable=True,
    )

    portfolio_url = Column(
        String(500),
        nullable=True,
    )

    location = Column(
        String(150),
        nullable=True,
    )

    bio = Column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # Resume
    #
    # Resume is parsed ONLY when:
    # 1. first uploaded
    # 2. user uploads an updated resume
    #
    # Show Jobs never parses resume again.
    # -----------------------------------------------------

    resume_filename = Column(
        String(500),
        nullable=True,
    )

    # Optional local/cloud path if we decide to keep
    # the original uploaded resume.
    resume_url = Column(
        String(1000),
        nullable=True,
    )

    # Extracted resume text.
    resume_text = Column(
        Text,
        nullable=True,
    )

    # Saved semantic vector.
    # This is compared with global Job.embedding vectors.
    resume_embedding = Column(
        ARRAY(Float),
        nullable=True,
    )

    # Last time the resume was parsed.
    resume_parsed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------
    # Experience
    # -----------------------------------------------------

    experience_type = Column(
        PgEnum(ExperienceType),
        default=ExperienceType.fresher,
        nullable=False,
    )

    years_of_experience = Column(
        Integer,
        nullable=True,
    )

    current_company = Column(
        String(150),
        nullable=True,
    )

    current_role = Column(
        String(150),
        nullable=True,
    )

    # -----------------------------------------------------
    # Education
    # -----------------------------------------------------

    highest_education = Column(
        String(150),
        nullable=True,
    )

    college = Column(
        String(250),
        nullable=True,
    )

    graduation_year = Column(
        Integer,
        nullable=True,
    )

    # -----------------------------------------------------
    # Skills
    #
    # Resume parser can update this when resume is uploaded.
    # User may also edit skills manually later.
    # -----------------------------------------------------

    skills = Column(
        ARRAY(String),
        nullable=True,
        default=list,
    )

    # Roles user is interested in.
    # Helpful for ranking/filtering.
    preferred_roles = Column(
        ARRAY(String),
        nullable=True,
        default=list,
    )

    # -----------------------------------------------------
    # Account status
    # -----------------------------------------------------

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )