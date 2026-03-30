import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)

    title      = Column(String(500), nullable=False)
    company    = Column(String(300), nullable=True)
    location   = Column(String(300), nullable=True)
    salary     = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    url        = Column(String(1000), nullable=True)

    # 'internshala' | 'naukri'
    source     = Column(String(50), nullable=False, index=True)
    # which skill query produced this result
    skill_query = Column(String(200), nullable=True)

    scraped_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Don't insert the same URL twice for the same user
        UniqueConstraint("user_id", "url", name="uq_user_job_url"),
    )
