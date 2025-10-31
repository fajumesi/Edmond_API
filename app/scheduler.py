"""
Background Scheduler
Manages automated daily updates of eCFR data
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from .fetcher import fetch_and_update_data

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def start_scheduler():
    """
    Start the background scheduler for daily data updates
    
    Schedules data fetch to run daily at 2 AM UTC
    """
    global scheduler
    
    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler already running")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Schedule daily update at 2 AM UTC
    # This ensures data is updated within 24 hours of eCFR changes
    scheduler.add_job(
        fetch_and_update_data,
        trigger=CronTrigger(hour=2, minute=0),  # Daily at 2:00 AM UTC
        id='daily_data_update',
        name='Daily eCFR data update',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    # Optional: Add more frequent update for testing (every 6 hours)
    # Uncomment for more frequent updates in production
    # scheduler.add_job(
    #     fetch_and_update_data,
    #     trigger=CronTrigger(hour='*/6'),  # Every 6 hours
    #     id='frequent_data_update',
    #     name='Frequent eCFR data update',
    #     replace_existing=True,
    #     max_instances=1
    # )
    
    scheduler.start()
    logger.info("Background scheduler started successfully")
    logger.info(f"Next scheduled update: {scheduler.get_job('daily_data_update').next_run_time}")

def stop_scheduler():
    """
    Stop the background scheduler
    """
    global scheduler
    
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")
        scheduler = None
    else:
        logger.warning("Scheduler not running")

def get_scheduler_status():
    """
    Get current scheduler status and job information
    
    Returns:
        Dictionary with scheduler status
    """
    global scheduler
    
    if scheduler is None or not scheduler.running:
        return {
            "running": False,
            "jobs": []
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "running": True,
        "jobs": jobs
    }

if __name__ == "__main__":
    # Test the scheduler
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
    
    try:
        # Keep running
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        stop_scheduler()
