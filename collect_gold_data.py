#!/usr/bin/env python3
"""
Gold Data Collection Script - Fetch and Store Last Year's 5-Minute Data
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.capital import CapitalAPIService
from app.services.database import DatabaseService
from app.services.data_fetcher import GoldDataFetcher
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GoldDataCollector:
    """Collects and stores historical gold data systematically"""

    def __init__(self):
        self.capital_service = None
        self.database_service = None
        self.data_fetcher = None
        self.total_records = 0
        self.total_batches = 0
        self.failed_batches = 0

    async def initialize(self):
        """Initialize all services"""
        logger.info("🚀 Initializing Gold Data Collector...")

        # Initialize database service first
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

    async def collect_year_data(self, start_months_back: int = 12):
        """
        Collect last year's 5-minute gold data in small batches

        Args:
            start_months_back: How many months back to start from (default 12 for 1 year)
        """
        logger.info(
            f"🎯 Starting collection of {start_months_back} months of 5-minute gold data"
        )

        # Calculate the date range
        end_date = datetime.now() - timedelta(days=7)  # Start from 1 week ago
        start_date = end_date - timedelta(
            days=30 * start_months_back
        )  # Go back N months

        logger.info(
            f"📅 Collection period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )

        # Use 6-hour batches to avoid API limits but get good coverage
        batch_hours = 6
        current_end = end_date
        batch_num = 0

        while current_end > start_date:
            batch_num += 1
            current_start = max(current_end - timedelta(hours=batch_hours), start_date)

            logger.info(
                f"📦 Processing batch {batch_num}: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}"
            )

            try:
                # Fetch data for this batch
                data = await self.data_fetcher.fetch_historical_prices(
                    epic="GOLD",
                    resolution="MINUTE_5",
                    max_pages=1,  # Use single page per batch to avoid API limits
                    from_date=current_start,
                    to_date=current_end,
                )

                if data:
                    # Store data in database
                    stored_count = await self.store_batch_data(data)
                    self.total_records += stored_count
                    logger.info(f"✅ Batch {batch_num}: {stored_count} records stored")
                else:
                    logger.warning(f"⚠️ Batch {batch_num}: No data returned")
                    self.failed_batches += 1

                self.total_batches += 1

                # Rate limiting - be nice to the API
                await asyncio.sleep(2)  # Wait 2 seconds between batches

                # Log progress every 10 batches
                if batch_num % 10 == 0:
                    logger.info(
                        f"📊 Progress: {batch_num} batches processed, {self.total_records} records collected"
                    )

            except Exception as e:
                logger.error(f"❌ Batch {batch_num} failed: {e}")
                self.failed_batches += 1

                # If we get rate limited, wait longer
                if "429" in str(e) or "too many requests" in str(e).lower():
                    logger.warning("⏸️ Rate limited, waiting 60 seconds...")
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(5)  # Wait 5 seconds on other errors

            # Move to the next batch (go back in time)
            current_end = current_start

        # Final summary
        success_rate = (
            ((self.total_batches - self.failed_batches) / self.total_batches * 100)
            if self.total_batches > 0
            else 0
        )
        logger.info("🎊 Data collection completed!")
        logger.info(f"📊 Total batches: {self.total_batches}")
        logger.info(
            f"✅ Successful batches: {self.total_batches - self.failed_batches}"
        )
        logger.info(f"❌ Failed batches: {self.failed_batches}")
        logger.info(f"📈 Success rate: {success_rate:.1f}%")
        logger.info(f"💎 Total records collected: {self.total_records}")

    async def store_batch_data(self, data: List[Dict[str, Any]]) -> int:
        """Store a batch of data in the database"""
        try:
            stored_count = await self.database_service.store_minute_prices(data)
            return stored_count
        except Exception as e:
            logger.error(f"❌ Failed to store batch data: {e}")
            return 0

    async def get_collection_stats(self):
        """Get statistics about collected data"""
        try:
            stats = await self.database_service.get_data_statistics()
            logger.info("📊 Collection Statistics:")
            logger.info(
                f"   📅 Date range: {stats.get('min_date', 'N/A')} to {stats.get('max_date', 'N/A')}"
            )
            logger.info(f"   📈 Total records: {stats.get('total_records', 0):,}")
            logger.info(f"   📊 5-minute records: {stats.get('minute_records', 0):,}")
            logger.info(f"   💾 Database size: {stats.get('database_size', 'N/A')}")
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            return {}


async def main():
    """Main execution function"""
    print("🏅 Gold Data Collector - Historical 5-Minute Data")
    print("=" * 60)

    collector = GoldDataCollector()

    try:
        # Initialize services
        await collector.initialize()

        # Get current database stats
        print("\n📊 Current Database Status:")
        await collector.get_collection_stats()

        # Ask user for confirmation
        print(f"\n🎯 Ready to collect last year's 5-minute gold data")
        print(f"📝 This will:")
        print(f"   • Fetch data in 6-hour batches to respect API limits")
        print(f"   • Use 2-second delays between batches")
        print(f"   • Store all data in the PostgreSQL database")
        print(f"   • Take approximately 30-60 minutes to complete")
        print(f"   • Collect roughly 100,000+ data points")

        response = input(f"\nDo you want to proceed? (y/N): ").strip().lower()

        if response == "y":
            start_time = time.time()
            await collector.collect_year_data(start_months_back=12)
            end_time = time.time()

            print(
                f"\n⏱️ Collection completed in {(end_time - start_time)/60:.1f} minutes"
            )

            # Show final statistics
            print(f"\n📊 Final Database Statistics:")
            await collector.get_collection_stats()

        else:
            print(f"📝 Collection cancelled by user")

    except Exception as e:
        logger.error(f"❌ Collection failed: {e}")
        print(f"❌ Error: {e}")

    finally:
        await collector.cleanup()
        print(f"\n✅ Gold Data Collector shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
