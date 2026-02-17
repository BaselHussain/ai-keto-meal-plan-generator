"""
Background job scheduler with SLA monitoring.
This is the primary background worker that handles scheduled jobs like
SLA monitoring every 15 minutes.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

import sentry_sdk

from src.lib.env import settings
from src.services.sla_monitoring_service import run_sla_monitoring

logger = logging.getLogger(__name__)

# Configure Sentry if available
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )


async def scheduled_sla_monitor() -> None:
    """
    Run SLA monitoring task every 15 minutes.
    This checks for manual_resolution entries where sla_deadline has been exceeded
    and processes auto-refunds for SLA violations.
    """
    logger.info("Starting SLA monitoring scheduler")

    # Run immediately at startup
    await _run_sla_monitor()

    while True:
        try:
            # Wait 15 minutes before running again
            logger.info("SLA monitor sleeping for 15 minutes...")
            await asyncio.sleep(15 * 60)  # 15 minutes in seconds

            await _run_sla_monitor()
        except asyncio.CancelledError:
            logger.info("SLA monitoring scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Error in SLA monitoring scheduler: {e}")
            sentry_sdk.capture_exception(e)
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)


async def _run_sla_monitor() -> None:
    """Execute single SLA monitoring run with error handling."""
    try:
        logger.info("Running scheduled SLA monitoring task")
        result = await run_sla_monitoring()
        logger.info(f"SLA monitoring completed: {result}")
    except Exception as e:
        logger.error(f"Error running SLA monitoring: {e}")
        sentry_sdk.capture_exception(e)


def signal_handler():
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal")
    sys.exit(0)


async def main():
    """Main function to run background jobs scheduler."""
    # Setup signal handlers
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())

    logger.info("Background jobs scheduler starting...")

    # Create and run the scheduled tasks concurrently
    await scheduled_sla_monitor()


if __name__ == "__main__":
    asyncio.run(main())