#!/usr/bin/env python3
"""
Historical Data Fetcher Script
Fetches last year of minute-by-minute gold data and stores it in the database
"""

import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.capital import CapitalAPIService
from app.services.database import DatabaseService
from app.services.data_fetcher import GoldDataFetcher
from app.core.config import settings
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)


class HistoricalDataManager:
    """Manages fetching and storing historical gold data"""

    def __init__(self):
        self.capital_service = None
        self.database_service = None
        self.data_fetcher = None

    async def initialize(self):
        """Initialize all services"""
        logger.info("🚀 Initializing Historical Data Manager...")

        # Initialize services
        self.database_service = DatabaseService()
        await self.database_service.initialize()

        self.capital_service = CapitalAPIService()
        await self.capital_service.initialize()

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

    async def fetch_year_data(self, epic: str = "GOLD", resolution: str = "MINUTE"):
        """
        Fetch last year of data for the specified epic and resolution

        Args:
            epic: Market epic (default: GOLD)
            resolution: Data resolution (MINUTE for minute-by-minute)
        """
        logger.info(f"📊 Starting to fetch last year of {resolution} data for {epic}")

        # Calculate date range - last year
        end_date = datetime.now() - timedelta(days=30)  # Go back 30 days from current
        start_date = end_date - timedelta(days=365)  # Go back 1 year from there

        logger.info(
            f"📅 Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )

        total_records_fetched = 0
        total_records_inserted = 0
        total_batches = 0
        start_time = time.time()

        # Log the start of fetch operation
        log_id = await self.database_service.log_fetch_operation(
            epic=epic,
            resolution=resolution,
            from_date=start_date,
            to_date=end_date,
            status="started",
        )

        try:
            # Fetch data in batches (going backwards from end_date)
            current_end = end_date
            batch_size_days = 7  # Fetch 7 days at a time to avoid API limits

            while current_end > start_date:
                current_start = current_end - timedelta(days=batch_size_days)
                if current_start < start_date:
                    current_start = start_date

                logger.info(
                    f"📦 Batch {total_batches + 1}: Fetching {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}"
                )

                try:
                    # Fetch data for this batch
                    batch_data = await self.data_fetcher.fetch_historical_prices(
                        epic=epic,
                        resolution=resolution,
                        max_pages=50,  # Increase max pages for more data
                        from_date=current_start,
                        to_date=current_end,
                    )

                    if batch_data:
                        logger.info(
                            f"📥 Fetched {len(batch_data)} records for batch {total_batches + 1}"
                        )
                        total_records_fetched += len(batch_data)

                        # Store data in database
                        if resolution == "MINUTE":
                            inserted = await self.database_service.insert_minute_prices(
                                epic, batch_data
                            )
                        else:
                            inserted = await self.database_service.insert_hour_prices(
                                epic, batch_data
                            )

                        total_records_inserted += inserted
                        logger.info(f"💾 Inserted {inserted} records to database")

                    else:
                        logger.warning(
                            f"⚠️ No data returned for batch {total_batches + 1}"
                        )

                    total_batches += 1

                    # Small delay to respect API rate limits
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"❌ Error processing batch {total_batches + 1}: {e}")

                # Move to next batch (go backwards in time)
                current_end = current_start

                # Progress update every 10 batches
                if total_batches % 10 == 0:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"📊 Progress: {total_batches} batches, {total_records_fetched} fetched, {total_records_inserted} inserted ({elapsed:.1f}s)"
                    )

            # Final statistics
            total_time = time.time() - start_time
            logger.info(f"✅ Data fetch completed!")
            logger.info(f"📊 Total batches: {total_batches}")
            logger.info(f"📥 Total records fetched: {total_records_fetched}")
            logger.info(f"💾 Total records inserted: {total_records_inserted}")
            logger.info(f"⏱️ Total time: {total_time:.1f} seconds")

            # Update fetch log
            await self.database_service.log_fetch_operation(
                epic=epic,
                resolution=resolution,
                from_date=start_date,
                to_date=end_date,
                records_fetched=total_records_fetched,
                records_inserted=total_records_inserted,
                duration_seconds=int(total_time),
                status="completed",
            )

            # Get database statistics
            stats = await self.database_service.get_database_stats()
            logger.info("📈 Database Statistics:")
            logger.info(f"   Minute records: {stats.get('minute_records', 0):,}")
            logger.info(f"   Hour records: {stats.get('hour_records', 0):,}")
            logger.info(f"   Daily records: {stats.get('daily_records', 0):,}")
            if stats.get("earliest_minute"):
                logger.info(f"   Earliest minute data: {stats['earliest_minute']}")
            if stats.get("latest_minute"):
                logger.info(f"   Latest minute data: {stats['latest_minute']}")

        except Exception as e:
            logger.error(f"❌ Fatal error during data fetch: {e}")

            # Update fetch log with error
            await self.database_service.log_fetch_operation(
                epic=epic,
                resolution=resolution,
                from_date=start_date,
                to_date=end_date,
                records_fetched=total_records_fetched,
                records_inserted=total_records_inserted,
                duration_seconds=int(time.time() - start_time),
                status="failed",
                error_message=str(e),
            )
            raise

    async def check_data_availability(self):
        """Check what data is available in the API"""
        logger.info("🔍 Checking data availability...")

        # Test different date ranges and resolutions - use very small ranges that work
        test_cases = [
            {
                "resolution": "MINUTE_5",
                "days_back": 0,
                "hours_back": 1,
            },  # 5-minute data for 1 hour
            {
                "resolution": "MINUTE_5",
                "days_back": 1,
                "hours_back": 0,
            },  # 5-minute data for 1 day (will use 1-hour batches)
            {
                "resolution": "HOUR",
                "days_back": 1,
                "hours_back": 0,
            },  # Hour data for 1 day
            {
                "resolution": "DAY",
                "days_back": 30,
                "hours_back": 0,
            },  # Daily data for 30 days
        ]

        for test in test_cases:
            try:
                end_date = datetime.now() - timedelta(days=30)

                # Calculate start date based on days_back and hours_back
                if test.get("hours_back", 0) > 0:
                    start_date = end_date - timedelta(hours=test["hours_back"])
                else:
                    start_date = end_date - timedelta(days=test["days_back"])

                logger.info(
                    f"🧪 Testing {test['resolution']} data for {test.get('hours_back', 0)} hours / {test.get('days_back', 0)} days back..."
                )

                data = await self.data_fetcher.fetch_historical_prices(
                    epic="GOLD",
                    resolution=test["resolution"],
                    max_pages=1,  # Just test with 1 page
                    from_date=start_date,
                    to_date=end_date,
                )

                if data:
                    logger.info(
                        f"✅ {test['resolution']}: {len(data)} records available"
                    )
                    logger.info(
                        f"   Date range: {data[0]['snapshotTime']} to {data[-1]['snapshotTime']}"
                    )
                else:
                    logger.warning(f"❌ {test['resolution']}: No data available")

            except Exception as e:
                logger.error(f"❌ {test['resolution']}: Error - {e}")

            await asyncio.sleep(0.5)


async def main():
    """Main function"""
    manager = HistoricalDataManager()

    try:
        await manager.initialize()

        # Check availability first
        await manager.check_data_availability()

        print("\n" + "=" * 60)
        print("🎯 READY TO FETCH LAST YEAR OF MINUTE DATA")
        print("=" * 60)

        # Ask user for confirmation
        response = input(
            "\nDo you want to proceed with fetching last year of minute-by-minute data? (y/N): "
        )

        if response.lower() in ["y", "yes"]:
            logger.info("🚀 Starting historical data fetch...")

            # Fetch minute-by-minute data for last year
            await manager.fetch_year_data(epic="GOLD", resolution="MINUTE_5")

            print("\n" + "=" * 60)
            print("✅ HISTORICAL DATA FETCH COMPLETED!")
            print("=" * 60)

        else:
            logger.info("🛑 Data fetch cancelled by user")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise

    finally:
        await manager.cleanup()


if __name__ == "__main__":
    print("🏅 Gold Trading Platform - Historical Data Fetcher")
    print("=" * 60)
    asyncio.run(main())
