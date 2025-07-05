"""
Gold Data Fetcher Service - Fetches historical data via API pagination
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import aiohttp
from ..core.config import settings
from ..core.logging import get_logger
from ..models.market import PriceTick, MarketData

logger = get_logger(__name__)


class GoldDataFetcher:
    """Service to fetch historical gold data using API pagination"""

    def __init__(self, capital_service):
        self.capital_service = capital_service
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize the data fetcher"""
        logger.info("🚀 Initializing Gold Data Fetcher")

        # Create aiohttp session
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)

        logger.info("✅ Gold Data Fetcher initialized")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        logger.info("✅ Gold Data Fetcher cleanup completed")

    async def fetch_historical_prices(
        self,
        epic: Optional[str] = None,
        resolution: str = "MINUTE_5",
        max_pages: int = 100,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical gold prices using pagination

        Args:
            epic: Market epic (instrument identifier) - if None, will try common gold epics
            resolution: Time resolution (MINUTE, MINUTE_5, HOUR, DAY)
            max_pages: Maximum number of pages to fetch
            from_date: Start date for historical data
            to_date: End date for historical data

        Returns:
            List of price data dictionaries
        """
        # Try different possible GOLD epics if none specified
        if epic is None:
            gold_epics = ["GOLD"]  # Use the working epic first
            for test_epic in gold_epics:
                logger.info(f"🔍 Trying epic: {test_epic}")
                result = await self._fetch_for_epic(
                    test_epic, resolution, max_pages, from_date, to_date
                )
                if result:
                    logger.info(f"✅ Successfully found data for epic: {test_epic}")
                    return result
                else:
                    logger.warning(f"❌ No data found for epic: {test_epic}")

            logger.error("❌ No valid gold epic found")
            return []
        else:
            return await self._fetch_for_epic(
                epic, resolution, max_pages, from_date, to_date
            )

    async def _fetch_for_epic(
        self,
        epic: str,
        resolution: str,
        max_pages: int,
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical prices for a specific epic
        """
        logger.info(f"📊 Starting historical data fetch for {epic}")
        logger.info(f"🔍 Resolution: {resolution}, Max pages: {max_pages}")

        # Ensure we're authenticated
        if not self.capital_service.is_authenticated:
            await self.capital_service.authenticate()

        all_prices = []

        # Adjust page size based on resolution to avoid API limits
        if resolution in ["MINUTE", "MINUTE_5"]:
            page_size = 500  # Good size for 5-minute data
        elif resolution == "HOUR":
            page_size = 1000  # Larger for hour data
        else:
            page_size = 1000  # Default for other resolutions

        current_page = 0

        # Set default date range if not provided - use VERY small ranges to avoid API limits
        if not to_date:
            to_date = datetime.now() - timedelta(days=30)  # Go back 30 days
        if not from_date:
            # Use very small ranges to avoid API limits - max 1 hour at a time
            if resolution in ["MINUTE", "MINUTE_5"]:
                from_date = to_date - timedelta(hours=1)  # 1 hour max for minute data
            elif resolution == "HOUR":
                from_date = to_date - timedelta(hours=12)  # 12 hours for hour data
            else:
                from_date = to_date - timedelta(days=7)  # 7 days for daily data

        logger.info(f"📅 Date range: {from_date.isoformat()} to {to_date.isoformat()}")

        headers = {
            "X-CAP-API-KEY": self.capital_service.api_key,
            "CST": self.capital_service.session_token,
            "X-SECURITY-TOKEN": self.capital_service.security_token,
            "Version": "1",
        }

        current_from = from_date
        current_to = to_date
        page_num = 0

        while page_num < max_pages and current_from < current_to:
            try:
                # Use the working date format: %Y-%m-%dT%H:%M:%S (no .000Z)
                from_timestamp = current_from.strftime("%Y-%m-%dT%H:%M:%S")
                to_timestamp = current_to.strftime("%Y-%m-%dT%H:%M:%S")

                # Build URL for historical prices
                url = f"{self.capital_service.base_url}/api/v1/prices/{epic}"
                params = {
                    "resolution": resolution,
                    "from": from_timestamp,
                    "to": to_timestamp,
                    "max": page_size,  # Use 'max' instead of pageSize
                }

                logger.info(f"📡 Fetching page {page_num + 1}/{max_pages} for {epic}")
                logger.info(f"📅 Date range: {from_timestamp} to {to_timestamp}")
                logger.debug(f"🔗 URL: {url}")
                logger.debug(f"📋 Params: {params}")

                async with self.session.get(
                    url, headers=headers, params=params
                ) as response:
                    if response.status == 401:
                        logger.warning(
                            "🔐 Authentication expired, re-authenticating..."
                        )
                        await self.capital_service.authenticate()
                        headers.update(
                            {
                                "CST": self.capital_service.session_token,
                                "X-SECURITY-TOKEN": self.capital_service.security_token,
                            }
                        )
                        continue

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"❌ API request failed for {epic}: {response.status} - {error_text}"
                        )
                        break

                    data = await response.json()

                    # Extract prices from response
                    prices = data.get("prices", [])
                    if not prices:
                        logger.info(
                            f"📭 No more data on page {page_num + 1} for {epic}"
                        )
                        break

                    logger.info(
                        f"✅ Retrieved {len(prices)} price records from page {page_num + 1} for {epic}"
                    )

                    # Process and store prices
                    processed_prices = self._process_price_data(prices, epic)
                    all_prices.extend(processed_prices)

                    # Check if we got less than expected (indicates we got all available data)
                    if len(prices) < page_size:
                        logger.info("📄 Reached last page of data")
                        break

                    # Update date range for next page (go further back in time)
                    # Find the oldest timestamp in current batch to avoid overlaps
                    oldest_time = min(
                        prices,
                        key=lambda x: x.get(
                            "snapshotTimeUTC", x.get("snapshotTime", "9999-12-31")
                        ),
                    )
                    oldest_dt = datetime.fromisoformat(
                        oldest_time.get(
                            "snapshotTimeUTC", oldest_time.get("snapshotTime", "")
                        ).replace("Z", "")
                    )

                    # Move the current_to to just before the oldest record
                    current_to = oldest_dt - timedelta(seconds=1)

                    # If we're going back too far, calculate a new from_date (use very small windows)
                    if resolution in ["MINUTE", "MINUTE_5"]:
                        current_from = current_to - timedelta(
                            hours=1
                        )  # 1 hour windows for minute data
                    elif resolution == "HOUR":
                        current_from = current_to - timedelta(
                            hours=12
                        )  # 12 hour windows for hour data
                    else:
                        current_from = current_to - timedelta(
                            days=7
                        )  # 7 days for daily data

                    page_num += 1

                    # Rate limiting - be nice to the API
                    await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"❌ Error fetching page {page_num + 1} for {epic}: {e}")
                break

        logger.info(
            f"🎯 Fetching completed for {epic}! Total records: {len(all_prices)}"
        )
        return all_prices

    def _process_price_data(
        self, prices: List[Dict], epic: str
    ) -> List[Dict[str, Any]]:
        """Process raw price data from API"""
        processed = []

        for price_data in prices:
            try:
                # Extract OHLC data
                open_price = price_data.get("openPrice", {})
                high_price = price_data.get("highPrice", {})
                low_price = price_data.get("lowPrice", {})
                close_price = price_data.get("closePrice", {})

                # Get bid/ask values
                open_bid = open_price.get("bid")
                open_ask = open_price.get("ask", open_price.get("offer"))

                high_bid = high_price.get("bid")
                high_ask = high_price.get("ask", high_price.get("offer"))

                low_bid = low_price.get("bid")
                low_ask = low_price.get("ask", low_price.get("offer"))

                close_bid = close_price.get("bid")
                close_ask = close_price.get("ask", close_price.get("offer"))

                # Get timestamp
                snapshot_time = price_data.get("snapshotTime")
                if not snapshot_time:
                    logger.debug(f"⚠️ No snapshotTime in record: {price_data}")
                    continue  # Skip records without timestamp

                timestamp = (
                    datetime.fromisoformat(snapshot_time.replace("Z", "+00:00"))
                    if snapshot_time
                    else datetime.now()
                )

                # Calculate mid prices
                open_mid = (open_bid + open_ask) / 2 if open_bid and open_ask else None
                high_mid = (high_bid + high_ask) / 2 if high_bid and high_ask else None
                low_mid = (low_bid + low_ask) / 2 if low_bid and low_ask else None
                close_mid = (
                    (close_bid + close_ask) / 2 if close_bid and close_ask else None
                )

                processed_record = {
                    "epic": epic,
                    "timestamp": timestamp,
                    "snapshot_time": snapshot_time,
                    # OHLC Bid prices
                    "open_bid": float(open_bid) if open_bid else None,
                    "high_bid": float(high_bid) if high_bid else None,
                    "low_bid": float(low_bid) if low_bid else None,
                    "close_bid": float(close_bid) if close_bid else None,
                    # OHLC Ask prices
                    "open_ask": float(open_ask) if open_ask else None,
                    "high_ask": float(high_ask) if high_ask else None,
                    "low_ask": float(low_ask) if low_ask else None,
                    "close_ask": float(close_ask) if close_ask else None,
                    # OHLC Mid prices
                    "open_mid": float(open_mid) if open_mid else None,
                    "high_mid": float(high_mid) if high_mid else None,
                    "low_mid": float(low_mid) if low_mid else None,
                    "close_mid": float(close_mid) if close_mid else None,
                    # Volume and last traded
                    "volume": price_data.get("lastTradedVolume"),
                    "last_traded": price_data.get("lastTradedPrice"),
                    # Raw data for reference
                    "raw_data": price_data,
                }

                processed.append(processed_record)

            except Exception as e:
                logger.error(f"❌ Error processing price record: {e}")
                logger.error(f"📋 Raw data: {price_data}")
                continue

        return processed

    async def fetch_recent_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch recent gold data for the specified number of hours"""
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=hours)

        return await self.fetch_historical_prices(
            from_date=from_date,
            to_date=to_date,
            max_pages=10,  # Limit pages for recent data
        )

    async def fetch_daily_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch daily gold data for the specified number of days"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        return await self.fetch_historical_prices(
            from_date=from_date,
            to_date=to_date,
            resolution="DAY",
            max_pages=5,  # Days need fewer pages
        )

    async def fetch_all_available_data(self) -> List[Dict[str, Any]]:
        """Fetch all available historical data (be careful with API limits!)"""
        logger.warning(
            "⚠️ Fetching ALL available data - this may take a while and consume API quota"
        )

        # Start from a reasonable historical date (e.g., 1 year ago)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=365)

        return await self.fetch_historical_prices(
            from_date=from_date,
            to_date=to_date,
            max_pages=1000,  # Allow many pages for historical data
            resolution="MINUTE_5",  # Use 5-minute resolution for balance of detail/volume
        )

    async def fetch_minute_data_batch(
        self, start_date: datetime, end_date: datetime, epic: str = "GOLD"
    ) -> List[Dict[str, Any]]:
        """
        Fetch minute data for a specific date range (max 1 day)
        This method handles the strict API limits for minute data
        """
        # Ensure date range is not more than 1 day
        if end_date - start_date > timedelta(days=1):
            logger.warning(f"⚠️ Date range too large for minute data, limiting to 1 day")
            start_date = end_date - timedelta(days=1)

        # Ensure we're not trying to get future data
        now = datetime.now()
        if end_date > now:
            end_date = now
        if start_date > now:
            start_date = now - timedelta(days=1)

        logger.info(
            f"📊 Fetching minute data for {epic} from {start_date} to {end_date}"
        )

        # Ensure we're authenticated
        if not self.capital_service.is_authenticated:
            await self.capital_service.authenticate()

        headers = {
            "X-CAP-API-KEY": self.capital_service.api_key,
            "CST": self.capital_service.session_token,
            "X-SECURITY-TOKEN": self.capital_service.security_token,
            "Version": "1",
        }

        try:
            # Use the working date format
            from_timestamp = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            to_timestamp = end_date.strftime("%Y-%m-%dT%H:%M:%S")

            url = f"{self.capital_service.base_url}/api/v1/prices/{epic}"
            params = {
                "resolution": "MINUTE",
                "from": from_timestamp,
                "to": to_timestamp,
                "max": 50,  # Very small batch for minute data
            }

            logger.info(f"📡 API Request: {from_timestamp} to {to_timestamp}")

            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 401:
                    logger.warning("🔐 Authentication expired, re-authenticating...")
                    await self.capital_service.authenticate()
                    return []

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"❌ API request failed: {response.status} - {error_text}"
                    )
                    return []

                data = await response.json()
                prices = data.get("prices", [])

                if prices:
                    logger.info(f"✅ Retrieved {len(prices)} minute records")
                    return self._process_price_data(prices, epic)
                else:
                    logger.info(f"📭 No minute data available for this period")
                    return []

        except Exception as e:
            logger.error(f"❌ Error fetching minute data: {e}")
            return []

    async def fetch_last_year_minute_data(
        self, epic: str = "GOLD", progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Fetch the last year of minute data by breaking it into small batches
        """
        logger.info(f"🚀 Starting to fetch last year of minute data for {epic}")

        all_data = []

        # Start from 1 year ago and work forward
        end_date = datetime.now() - timedelta(
            days=30
        )  # Start 30 days ago (avoid recent data issues)
        start_date = end_date - timedelta(days=365)  # Go back 1 year

        current_start = start_date
        batch_count = 0
        total_records = 0

        # Process in 1-day batches
        while current_start < end_date:
            batch_count += 1
            current_end = min(current_start + timedelta(days=1), end_date)

            logger.info(
                f"📅 Batch {batch_count}: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}"
            )

            if progress_callback:
                progress = ((current_start - start_date).days / 365) * 100
                progress_callback(progress, batch_count, current_start, current_end)

            # Fetch this batch
            batch_data = await self.fetch_minute_data_batch(
                epic, current_start, current_end
            )

            if batch_data:
                all_data.extend(batch_data)
                total_records += len(batch_data)
                logger.info(
                    f"✅ Batch {batch_count}: {len(batch_data)} records (Total: {total_records})"
                )
            else:
                logger.warning(f"⚠️ Batch {batch_count}: No data")

            # Move to next day
            current_start = current_end

            # Rate limiting - be very gentle with the API
            await asyncio.sleep(1.0)  # 1 second between requests

            # Stop if we have a reasonable amount of data for testing
            if total_records > 10000:  # Stop at 10k records for initial testing
                logger.info(f"🛑 Stopping at {total_records} records for testing")
                break

        logger.info(
            f"🎯 Completed fetching minute data! Total records: {len(all_data)}"
        )
        return all_data

    # ...existing code...
