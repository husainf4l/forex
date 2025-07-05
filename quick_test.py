#!/usr/bin/env python3
"""
Quick test of the data fetcher
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.capital import CapitalAPIService
from app.services.data_fetcher import GoldDataFetcher
from datetime import datetime, timedelta


async def quick_test():
    capital_service = CapitalAPIService()
    await capital_service.initialize()

    fetcher = GoldDataFetcher(capital_service)
    await fetcher.initialize()

    # Test with last month's data (more recent, higher chance of availability)
    end_date = datetime.now() - timedelta(days=7)  # 1 week ago
    start_date = end_date - timedelta(hours=1)  # 1 hour window

    print(f"Testing date range: {start_date} to {end_date}")

    data = await fetcher.fetch_historical_prices(
        epic="GOLD",
        resolution="MINUTE_5",
        max_pages=1,
        from_date=start_date,
        to_date=end_date,
    )

    print(f"Got {len(data)} records")
    if data:
        print(f"Sample record: {data[0]}")

    await fetcher.cleanup()
    await capital_service.cleanup()


if __name__ == "__main__":
    asyncio.run(quick_test())
