from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from .services.tracker import daily_update

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        daily_update,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_etsy_tracker",
        replace_existing=True
    )
    scheduler.start()
    logger.info("APScheduler started. Daily tracker scheduled for midnight.")
