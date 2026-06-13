import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.config import settings
from das.scheduler import run_sync_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_sync_cycle, "interval", minutes=settings.sync_interval_minutes, id="sync")
    scheduler.start()
    logging.getLogger(__name__).info(
        "DAS started — sync every %d minutes", settings.sync_interval_minutes
    )
    # Run once immediately on startup
    await run_sync_cycle()
    # Keep running
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
