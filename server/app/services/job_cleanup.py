import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models.job import Job

logger = logging.getLogger(__name__)

async def delete_old_jobs():
    """Delete jobs with scraped_at older than 7 days."""
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(delete(Job).where(Job.scraped_at < cutoff))
        await db.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(f"🗑️ Deleted {deleted} job(s) older than 7 days.")
        return deleted

async def run_cleanup_every_24h():
    """Run cleanup every 24 hours."""
    while True:
        try:
            await delete_old_jobs()
        except Exception as e:
            logger.exception(f"Cleanup error: {e}")
        await asyncio.sleep(24 * 3600)