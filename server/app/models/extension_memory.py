import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class ExtensionMemory(Base):
    __tablename__ = "extension_memory"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Current CareerSync user
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Original question/label seen on the form
    question = Column(
        Text,
        nullable=False,
    )

    # Normalized version used for matching
    normalized_question = Column(
        String(500),
        nullable=False,
        index=True,
    )

    # Saved user answer
    answer = Column(
        Text,
        nullable=False,
    )

    # Extra context from the HTML field
    field_context = Column(
        JSONB,
        nullable=True,
    )

    # Example values:
    # manual
    # learned
    # profile
    source = Column(
        String(50),
        nullable=False,
        default="manual",
    )

    confidence = Column(
        Float,
        nullable=False,
        default=1.0,
    )

    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    last_used = Column(
        DateTime(timezone=True),
        nullable=True,
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

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_question",
            name="uq_extension_memory_user_question",
        ),
    )