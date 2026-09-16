import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Index,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    title = Column(
        String(500),
        nullable=False,
    )

    company = Column(
        String(300),
        nullable=True,
    )

    location = Column(
        String(300),
        nullable=True,
        index=True,
    )

    salary = Column(
        String(200),
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    # Same job should not be stored repeatedly.
    url = Column(
        String(1000),
        nullable=True,
        unique=True,
        index=True,
    )

    # naukri / indeed / internshala
    source = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Discovery keyword only. It is NOT treated as a verified requirement.
    skill_query = Column(
        String(200),
        nullable=True,
        index=True,
    )

    # V2 semantic matching:
    # generated once for the global job and reused for every user.
    embedding = Column(
        ARRAY(Float),
        nullable=True,
    )

    scraped_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index(
            "idx_jobs_expiry",
            "expires_at",
        ),
        Index(
            "idx_jobs_source_scraped",
            "source",
            "scraped_at",
        ),
    )
