from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime

from app.database import Base


class UserJobMatch(Base):
    __tablename__ = "user_job_matches"

    id = Column(String, primary_key=True)

    user_id = Column(String, nullable=False, index=True)
    job_id = Column(String, nullable=False, index=True)

    match_score = Column(Float, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )