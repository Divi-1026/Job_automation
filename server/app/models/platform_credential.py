import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class PlatformCredential(Base):
    __tablename__ = "platform_credentials"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # naukri / indeed / etc.
    platform = Column(
        String(50),
        nullable=False,
        index=True,
    )

    email = Column(
        String(255),
        nullable=False,
    )

    # NEVER store plain password.
    password_encrypted = Column(
        String(1000),
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

    __table_args__ = (
        # One credential record per platform for one user.
        UniqueConstraint(
            "user_id",
            "platform",
            name="uq_user_platform_credential",
        ),
    )