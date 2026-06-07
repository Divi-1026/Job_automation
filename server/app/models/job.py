import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(500), nullable=False)
    company = Column(String(300), nullable=True)
    location = Column(String(300), nullable=True)
    salary = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True, unique=True)  # global unique URL
    source = Column(
        String(50), nullable=False, index=True
    )  # 'naukri', 'indeed', 'internshala'
    skill_query = Column(
        String(200), nullable=True, index=True
    )  # skill used to scrape this job
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    applied = Column(Boolean, default=False, index=True)

    __table_args__ = (
        Index("idx_jobs_deletion", "scraped_at"),  # for efficient cleanup
    )
