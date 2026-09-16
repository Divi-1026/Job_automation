import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExtensionProfile(Base):
    __tablename__ = "extension_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True
    )

    # Personal
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    date_of_birth: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Links
    linkedin: Mapped[str | None] = mapped_column(Text, nullable=True)
    github: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Education
    highest_qualification: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    college: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    graduation_year: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    degree: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True
    )

    branch: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True
    )

    cgpa: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    percentage: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    class10_percentage: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    class12_percentage: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    # Professional
    experience_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True
    )

    years_of_experience: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    current_company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    current_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Preferences
    preferred_roles: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    preferred_locations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    expected_ctc: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True
    )

    notice_period: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True
    )

    willing_to_relocate: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )