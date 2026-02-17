#!/usr/bin/env python3
"""Cleanup job: Delete unpaid quiz responses older than 7 days (T129).

Retention policy: quiz_responses where created_at < NOW() - 7d AND payment_id IS NULL.
Schedule: Daily
"""
import argparse
import asyncio
import logging
import os
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import sentry_sdk
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.lib.database import get_database_url

SCRIPT_NAME = "cleanup_unpaid_quiz"
BATCH_SIZE = int(os.getenv("CLEANUP_BATCH_SIZE", "100"))
RETENTION_DAYS = 7

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(SCRIPT_NAME)


def _init_sentry():
    dsn = os.getenv("SENTRY_BACKEND_DSN")
    if dsn:
        sentry_sdk.init(dsn=dsn, environment=os.getenv("ENV", "production"))


def _build_session_factory():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(get_database_url(), echo=False, connect_args={"ssl": ssl_ctx})
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _report(count, elapsed, dry_run):
    try:
        sentry_sdk.capture_message(
            f"Cleanup: {SCRIPT_NAME} deleted {count} records in {elapsed:.1f}s (dry_run={dry_run})",
            level="info",
        )
    except Exception:
        pass


async def cleanup(dry_run=False):
    from src.models.quiz_response import QuizResponse

    start = time.time()
    deleted = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    logger.info(f"Starting (dry_run={dry_run}). Cutoff: {cutoff.isoformat()}")

    sf = _build_session_factory()

    async with sf() as session:
        total = (await session.execute(
            select(func.count()).where(and_(
                QuizResponse.payment_id.is_(None),
                QuizResponse.created_at < cutoff
            ))
        )).scalar_one()
        logger.info(f"Total candidates: {total}")
        if total == 0:
            _report(0, time.time() - start, dry_run)
            return 0
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {total} records.")
            _report(total, time.time() - start, dry_run)
            return total

    while True:
        async with sf() as session:
            try:
                result = await session.execute(
                    select(QuizResponse.id).where(and_(
                        QuizResponse.payment_id.is_(None),
                        QuizResponse.created_at < cutoff
                    )).limit(BATCH_SIZE)
                )
                ids = [r[0] for r in result.fetchall()]
                if not ids:
                    break
                await session.execute(delete(QuizResponse).where(QuizResponse.id.in_(ids)))
                await session.commit()
                deleted += len(ids)
                logger.info(f"Processed {deleted}/{total}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Batch error: {e}", exc_info=True)
                sentry_sdk.capture_exception(e)
                break

    elapsed = time.time() - start
    logger.info(f"Deleted {deleted} in {elapsed:.1f}s")
    _report(deleted, elapsed, dry_run)
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Delete unpaid quiz responses older than 7 days (T129)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _init_sentry()
    asyncio.run(cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
