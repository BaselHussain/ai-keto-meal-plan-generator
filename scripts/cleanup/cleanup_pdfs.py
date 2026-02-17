#!/usr/bin/env python3
"""Cleanup job: Delete Vercel Blob PDFs for meal plans older than 91 days (T131).

Retention policy: meal_plans where created_at < NOW() - 91 days AND pdf_blob_path IS NOT NULL.
Deletes blob from Vercel, then nulls pdf_blob_path. 91d = 90d retention + 24h grace.
Schedule: Daily at 00:00 UTC
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
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.lib.database import get_database_url

SCRIPT_NAME = "cleanup_pdfs"
BATCH_SIZE = int(os.getenv("CLEANUP_BATCH_SIZE", "100"))
RETENTION_DAYS = 91

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
            f"Cleanup: {SCRIPT_NAME} processed {count} blob deletions in {elapsed:.1f}s (dry_run={dry_run})",
            level="info",
        )
    except Exception:
        pass


async def cleanup(dry_run=False):
    from src.models.meal_plan import MealPlan
    from src.services.blob_storage import delete_blob, BlobStorageError

    start = time.time()
    processed = 0
    blob_deleted = 0
    blob_failed = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    logger.info(f"Starting (dry_run={dry_run}). Cutoff: {cutoff.isoformat()}")

    sf = _build_session_factory()

    async with sf() as session:
        total = (await session.execute(
            select(func.count()).where(and_(
                MealPlan.created_at < cutoff,
                MealPlan.pdf_blob_path.isnot(None)
            ))
        )).scalar_one()
        logger.info(f"Total candidates: {total}")
        if total == 0:
            _report(0, time.time() - start, dry_run)
            return 0
        if dry_run:
            logger.info(f"[DRY RUN] Would process {total} blob deletions.")
            _report(total, time.time() - start, dry_run)
            return total

    while True:
        async with sf() as session:
            try:
                result = await session.execute(
                    select(MealPlan.id, MealPlan.pdf_blob_path).where(and_(
                        MealPlan.created_at < cutoff,
                        MealPlan.pdf_blob_path.isnot(None)
                    )).limit(BATCH_SIZE)
                )
                batch = result.fetchall()
                if not batch:
                    break

                cleared_ids = []
                for mp_id, blob_path in batch:
                    try:
                        deleted = await delete_blob(blob_path)
                        if deleted:
                            blob_deleted += 1
                        else:
                            logger.warning(f"Blob not found (already deleted): {blob_path}")
                        cleared_ids.append(mp_id)
                    except BlobStorageError as e:
                        blob_failed += 1
                        logger.error(f"Blob deletion failed for {blob_path}: {e}")
                        sentry_sdk.capture_exception(e)

                if cleared_ids:
                    await session.execute(
                        update(MealPlan).where(MealPlan.id.in_(cleared_ids)).values(pdf_blob_path=None)
                    )
                    await session.commit()
                    processed += len(cleared_ids)
                    logger.info(f"Processed {processed}/{total} (deleted={blob_deleted}, failed={blob_failed})")

            except Exception as e:
                await session.rollback()
                logger.error(f"Batch error: {e}", exc_info=True)
                sentry_sdk.capture_exception(e)
                break

    elapsed = time.time() - start
    logger.info(f"Completed: {processed} processed, {blob_deleted} deleted, {blob_failed} failed in {elapsed:.1f}s")
    _report(processed, elapsed, dry_run)
    return processed


def main():
    parser = argparse.ArgumentParser(description="Delete Vercel Blob PDFs older than 91 days (T131)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _init_sentry()
    asyncio.run(cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
