from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    UniqueConstraint,
)

from app.database import Base


class UserApplication(Base):
    """
    User-specific application history.

    We intentionally store user_id and job_id as VARCHAR without
    database ForeignKey constraints because the existing users/jobs
    primary keys are UUIDs while the application-history router works
    with their string representations.

    This avoids PostgreSQL UUID/VARCHAR foreign-key type mismatch
    while still keeping one unique history row per user/job pair.
    """

    __tablename__ = "user_applications"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String,
        nullable=False,
        index=True,
    )

    job_id = Column(
        String,
        nullable=False,
        index=True,
    )

    status = Column(
        String,
        nullable=False,
        default="pending_manual",
        index=True,
    )

    note = Column(
        String,
        nullable=True,
    )

    manual_url = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_id",
            name="uq_user_application_user_job",
        ),
    )
