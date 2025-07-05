#!/usr/bin/env python3
"""
Script to fetch and store the last year of minute-by-minute gold data
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.services.capital import CapitalAPIService
from app.services.database import DatabaseService
from app.services.data_fetcher import GoldDataFetcher
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GoldDataBackfiller:
    """Service to backfill historical gold data"""

    def __init__(self):
        self.capital_service = None
        self.database_service = None
        self.data_fetcher = None

    async def initialize(self):
        """Initialize all services"""
        logger.info("🚀 Initializing Gold Data Backfiller...")

        # Initialize database service
        self.database_service = DatabaseService()
        await self.database_service.initialize()

        # Initialize Capital service
        self.capital_service = CapitalAPIService()
        await self.capital_service.initialize()

        # Initialize data fetcher
        self.data_fetcher = GoldDataFetcher(self.capital_service)
        await self.data_fetcher.initialize()

        logger.info("✅ All services initialized successfully!")

    async def cleanup(self):
        """Cleanup all services"""
        if self.data_fetcher:
            await self.data_fetcher.cleanup()
        if self.capital_service:
            await self.capital_service.cleanup()
        if self.database_service:
            await self.database_service.cleanup()
        logger.info("✅ All services cleaned up")

    async def fetch_and_store_historical_data(
        self,
        epic: str = "GOLD",
        resolution: str = "MINUTE",
        days_back: int = 365,
        chunk_size_days: int = 30,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Fetch and store historical gold data

        Args:
            epic: Market epic
            resolution: Data resolution (MINUTE, HOUR, DAY)
            days_back: Number of days to go back
            chunk_size_days: Number of days to fetch per chunk
            max_retries: Maximum retry attempts per chunk

        Returns:
            Summary of the operation
        """

        logger.info(f"📊 Starting historical data fetch for {epic}")
        logger.info(f"⏰ Fetching {days_back} days of {resolution} data")
        logger.info(f"📦 Chunk size: {chunk_size_days} days")

        # Calculate date range
        end_date = datetime.now() - timedelta(days=1)  # Start from yesterday
        start_date = end_date - timedelta(days=days_back)

        logger.info(
            f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )

        # Statistics
        total_records_fetched = 0
        total_records_inserted = 0
        total_chunks = 0
        failed_chunks = 0
        start_time = time.time()

        # Process data in chunks
        current_end = end_date

        while current_end > start_date:
            # Calculate chunk boundaries
            current_start = max(
                current_end - timedelta(days=chunk_size_days), start_date
            )
            total_chunks += 1

            logger.info(f"\n📖 Processing chunk {total_chunks}")
            logger.info(
                f"📅 Chunk range: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}"
            )

            # Fetch data for this chunk
            chunk_success = False
            retry_count = 0

            while not chunk_success and retry_count < max_retries:
                try:
                    # Log fetch operation start
                    fetch_log_id = await self.database_service.log_fetch_operation(
                        epic=epic,
                        resolution=resolution,
                        from_date=current_start,
                        to_date=current_end,
                        status="started",
                    )

                    chunk_start_time = time.time()

                    # Fetch data
                    logger.info(
                        f"🔄 Fetching data (attempt {retry_count + 1}/{max_retries})..."
                    )

                    chunk_data = await self.data_fetcher.fetch_historical_prices(
                        epic=epic,
                        resolution=resolution,
                        max_pages=5,  # Limit pages per chunk
                        from_date=current_start,
                        to_date=current_end,
                    )

                    chunk_duration = int(time.time() - chunk_start_time)

                    if chunk_data:
                        logger.info(
                            f"✅ Fetched {len(chunk_data)} records for chunk {total_chunks}"
                        )

                        # Store data in database
                        if resolution == "MINUTE":
                            inserted_count = (
                                await self.database_service.insert_minute_prices(
                                    epic, chunk_data
                                )
                            )
                        elif resolution == "HOUR":
                            inserted_count = (
                                await self.database_service.insert_hour_prices(
                                    epic, chunk_data
                                )
                            )
                        else:
                            logger.warning(
                                f"⚠️ Unsupported resolution: {resolution}, skipping storage"
                            )
                            inserted_count = 0

                        # Update statistics
                        total_records_fetched += len(chunk_data)
                        total_records_inserted += inserted_count

                        # Log successful fetch
                        await self.database_service.log_fetch_operation(
                            epic=epic,
                            resolution=resolution,
                            from_date=current_start,
                            to_date=current_end,
                            records_fetched=len(chunk_data),
                            records_inserted=inserted_count,
                            duration_seconds=chunk_duration,
                            status="completed",
                        )

                        chunk_success = True
                        logger.info(f"💾 Stored {inserted_count} records in database")

                    else:
                        logger.warning(f"⚠️ No data returned for chunk {total_chunks}")

                        # Log failed fetch
                        await self.database_service.log_fetch_operation(
                            epic=epic,
                            resolution=resolution,
                            from_date=current_start,
                            to_date=current_end,
                            records_fetched=0,
                            records_inserted=0,
                            duration_seconds=chunk_duration,
                            status="no_data",
                        )

                        # Still consider this a success (no data available)
                        chunk_success = True

                except Exception as e:
                    retry_count += 1
                    logger.error(
                        f"❌ Error fetching chunk {total_chunks} (attempt {retry_count}): {e}"
                    )

                    if retry_count >= max_retries:
                        failed_chunks += 1
                        logger.error(
                            f"❌ Failed to fetch chunk {total_chunks} after {max_retries} attempts"
                        )

                        # Log failed fetch
                        await self.database_service.log_fetch_operation(
                            epic=epic,
                            resolution=resolution,
                            from_date=current_start,
                            to_date=current_end,
                            records_fetched=0,
                            records_inserted=0,
                            duration_seconds=0,
                            status="failed",
                            error_message=str(e),
                        )

                    else:
                        # Wait before retry
                        await asyncio.sleep(2**retry_count)  # Exponential backoff

            # Move to next chunk
            current_end = current_start - timedelta(minutes=1)

            # Progress update
            elapsed_time = time.time() - start_time
            progress = (
                (end_date - current_end).total_seconds()
                / (end_date - start_date).total_seconds()
            ) * 100

            logger.info(
                f"📊 Progress: {progress:.1f}% | Records: {total_records_fetched} | Time: {elapsed_time:.1f}s"
            )

            # Small delay to avoid overwhelming the API
            await asyncio.sleep(1)

        # Final statistics
        total_time = time.time() - start_time

        summary = {
            "epic": epic,
            "resolution": resolution,
            "total_chunks": total_chunks,
            "successful_chunks": total_chunks - failed_chunks,
            "failed_chunks": failed_chunks,
            "total_records_fetched": total_records_fetched,
            "total_records_inserted": total_records_inserted,
            "total_time_seconds": int(total_time),
            "average_records_per_minute": (
                total_records_fetched / (total_time / 60) if total_time > 0 else 0
            ),
        }

        logger.info(f"\n🎉 Historical data fetch completed!")
        logger.info(f"📊 Summary: {summary}")

        return summary

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        if not self.database_service:
            return {"error": "Database service not initialized"}
        return await self.database_service.get_database_stats()


async def main():
    """Main function to run the backfill process"""

    print("🚀 Starting Gold Data Backfill Process...")
    print("=" * 60)

    backfiller = GoldDataBackfiller()

    try:
        # Initialize services
        await backfiller.initialize()

        # Show current database stats
        print("\n📊 Current Database Statistics:")
        stats = await backfiller.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Ask user for confirmation
        print("\n⚠️  This will drop all existing tables and recreate them!")
        print("Are you sure you want to continue? (y/N): ", end="")

        # For automation, we'll proceed automatically
        # In interactive mode, you'd want to check user input
        proceed = True  # input().lower().strip() == 'y'

        if not proceed:
            print("❌ Operation cancelled by user")
            return

        print("\n🔄 Starting data backfill...")

        # Fetch MINUTE data for the last year
        summary = await backfiller.fetch_and_store_historical_data(
            epic="GOLD",
            resolution="MINUTE",
            days_back=365,
            chunk_size_days=7,  # Smaller chunks for minute data
            max_retries=3,
        )

        print("\n✅ Backfill completed successfully!")
        print("📊 Final Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Show final database stats
        print("\n📊 Final Database Statistics:")
        final_stats = await backfiller.get_database_stats()
        for key, value in final_stats.items():
            print(f"  {key}: {value}")

    except Exception as e:
        logger.error(f"❌ Backfill process failed: {e}")
        print(f"❌ Error: {e}")

    finally:
        # Cleanup
        await backfiller.cleanup()
        print("\n✅ Cleanup completed!")


if __name__ == "__main__":
    asyncio.run(main())
