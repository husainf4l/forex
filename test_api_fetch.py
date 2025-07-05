#!/usr/bin/env python3
"""
Test script to fetch gold data from Capital.com API using pagination
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# Capital.com API configuration
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_DEMO = os.getenv("CAPITAL_DEMO", "false").lower() == "true"

# API endpoints
if CAPITAL_DEMO:
    BASE_URL = "https://demo-api-capital.backend-capital.com"
else:
    BASE_URL = "https://api-capital.backend-capital.com"

LOGIN_URL = f"{BASE_URL}/api/v1/session"
PRICES_URL = f"{BASE_URL}/api/v1/prices"


class CapitalAPITester:
    """Test Capital.com API for fetching historical data"""

    def __init__(self):
        self.session = None
        self.headers = {
            "X-CAP-API-KEY": CAPITAL_API_KEY,
            "Content-Type": "application/json",
        }
        self.cst_token = None
        self.x_security_token = None

    async def initialize(self):
        """Initialize session and login"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Login to get session tokens
        await self.login()

    async def cleanup(self):
        """Cleanup session"""
        if self.session:
            await self.session.close()

    async def login(self):
        """Login to Capital.com API"""
        login_data = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}

        print(f"🔐 Logging in to Capital.com API...")
        print(f"📡 Base URL: {BASE_URL}")
        print(f"🧪 Demo mode: {CAPITAL_DEMO}")

        try:
            async with self.session.post(
                LOGIN_URL, json=login_data, headers=self.headers
            ) as response:
                print(f"📊 Login response status: {response.status}")

                if response.status == 200:
                    # Get session tokens from headers
                    self.cst_token = response.headers.get("CST")
                    self.x_security_token = response.headers.get("X-SECURITY-TOKEN")

                    if self.cst_token and self.x_security_token:
                        # Update headers with session tokens
                        self.headers["CST"] = self.cst_token
                        self.headers["X-SECURITY-TOKEN"] = self.x_security_token
                        print("✅ Login successful!")
                        return True
                    else:
                        print("❌ Login failed: Missing session tokens")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Login failed: {response.status} - {error_text}")
                    return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    async def search_markets(self, search_term: str = "gold"):
        """Search for markets containing the search term"""
        search_url = f"{BASE_URL}/api/v1/markets"
        params = {"searchTerm": search_term, "limit": 50}

        print(f"🔍 Searching for markets with term: {search_term}")

        try:
            async with self.session.get(
                search_url, params=params, headers=self.headers
            ) as response:
                print(f"📊 Search response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    markets = data.get("markets", [])

                    print(f"📈 Found {len(markets)} markets:")
                    for market in markets[:10]:  # Show first 10
                        print(
                            f"  - {market.get('epic', 'N/A')} | {market.get('instrumentName', 'N/A')} | {market.get('marketStatus', 'N/A')}"
                        )

                    return markets
                else:
                    error_text = await response.text()
                    print(f"❌ Search failed: {response.status} - {error_text}")
                    return []

        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    async def fetch_historical_data(
        self, epic: str, resolution: str = "MINUTE", days_back: int = 7
    ):
        """Fetch historical data for a specific epic"""

        # Use older dates that are more likely to have data
        # Go back 30 days to start, then back another 'days_back' days
        base_date = datetime.now() - timedelta(days=30)  # Start 30 days ago
        to_date = base_date
        from_date = to_date - timedelta(days=days_back)

        print(
            f"📅 Using date range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
        )

        # Try different date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO with microseconds and Z
            "%Y-%m-%dT%H:%M:%SZ",  # ISO with Z
            "%Y-%m-%dT%H:%M:%S",  # ISO without Z
            "%Y-%m-%d %H:%M:%S",  # Space separated
            "%Y-%m-%d",  # Date only
            "%d/%m/%Y",  # DD/MM/YYYY
            "%m/%d/%Y",  # MM/DD/YYYY
        ]

        for fmt in date_formats:
            try:
                from_str = from_date.strftime(fmt)
                to_str = to_date.strftime(fmt)

                print(f"🧪 Trying date format: {fmt}")
                print(f"📅 From: {from_str}, To: {to_str}")

                result = await self._fetch_with_format(
                    epic, resolution, from_str, to_str
                )
                if result is not None:
                    return result

            except Exception as e:
                print(f"❌ Date format {fmt} failed: {e}")
                continue

        return []

    async def _fetch_with_format(
        self, epic: str, resolution: str, from_str: str, to_str: str
    ):
        """Helper method to fetch data with specific date format"""

    async def _fetch_with_format(
        self, epic: str, resolution: str, from_str: str, to_str: str
    ):
        """Helper method to fetch data with specific date format"""

        prices_url = f"{PRICES_URL}/{epic}"
        params = {
            "resolution": resolution,
            "from": from_str,
            "to": to_str,
            "max": 1000,  # Maximum records per request
        }

        try:
            async with self.session.get(
                prices_url, params=params, headers=self.headers
            ) as response:
                print(f"📊 Response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    prices = data.get("prices", [])

                    print(f"✅ SUCCESS! Retrieved {len(prices)} price records")

                    if prices:
                        # Show first and last few records
                        print("\n🔍 Sample data:")
                        for i, price in enumerate(prices[:3]):
                            print(f"  [{i}] {price}")

                        if len(prices) > 6:
                            print("  ...")
                            for i, price in enumerate(prices[-3:], len(prices) - 3):
                                print(f"  [{i}] {price}")

                    return prices
                else:
                    error_text = await response.text()
                    print(f"❌ Failed: {response.status} - {error_text}")
                    return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    async def test_pagination(
        self, epic: str, resolution: str = "HOUR", max_pages: int = 3
    ):
        """Test pagination for historical data"""

        print(f"\n🔄 Testing pagination for epic: {epic}")

        all_prices = []
        page = 1

        # Start from 90 days back for better data availability
        to_date = datetime.now() - timedelta(days=30)
        from_date = to_date - timedelta(days=30)

        while page <= max_pages:
            print(f"\n📖 Fetching page {page}...")

            # Use the working date format
            from_str = from_date.strftime("%Y-%m-%dT%H:%M:%S")
            to_str = to_date.strftime("%Y-%m-%dT%H:%M:%S")

            prices_url = f"{PRICES_URL}/{epic}"
            params = {
                "resolution": resolution,
                "from": from_str,
                "to": to_str,
                "max": 500,  # Larger batch for testing
            }

            try:
                async with self.session.get(
                    prices_url, params=params, headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])

                        if not prices:
                            print(f"📭 No more data on page {page}")
                            break

                        print(f"📊 Page {page}: {len(prices)} records")
                        print(f"📅 Date range: {from_str} to {to_str}")

                        all_prices.extend(prices)

                        # Update date range for next page (go further back)
                        to_date = from_date
                        from_date = to_date - timedelta(days=30)

                        page += 1

                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)

                    else:
                        error_text = await response.text()
                        print(
                            f"❌ Page {page} failed: {response.status} - {error_text}"
                        )
                        break

            except Exception as e:
                print(f"❌ Page {page} error: {e}")
                break

        print(f"\n📊 Total records fetched: {len(all_prices)}")
        return all_prices


async def main():
    """Main test function"""

    print("🚀 Starting Capital.com API test for gold data fetching...")

    if not CAPITAL_API_KEY or not CAPITAL_EMAIL or not CAPITAL_PASSWORD:
        print("❌ Missing required environment variables!")
        print("Please set CAPITAL_API_KEY, CAPITAL_EMAIL, and CAPITAL_PASSWORD")
        return

    tester = CapitalAPITester()

    try:
        await tester.initialize()

        # First, search for gold markets
        markets = await tester.search_markets("gold")

        if markets:
            # Focus on GOLD epic first
            gold_epic = "GOLD"

            print(f"\n🧪 Testing historical data fetch for GOLD epic...")
            print(f"\n" + "=" * 50)

            data = await tester.fetch_historical_data(
                gold_epic, resolution="MINUTE", days_back=7
            )

            if data:
                print(f"✅ Successfully fetched {len(data)} records for {gold_epic}")

                # Test pagination for the working epic
                print(f"\n🔄 Testing pagination for {gold_epic}...")
                paginated_data = await tester.test_pagination(
                    gold_epic, resolution="HOUR", max_pages=3
                )
                print(
                    f"📊 Pagination test completed: {len(paginated_data)} total records"
                )

                # Save sample data to file
                if paginated_data:
                    sample_file = (
                        "/Users/al-husseinabdullah/Desktop/forex/sample_gold_data.json"
                    )
                    with open(sample_file, "w") as f:
                        json.dump(
                            paginated_data[:100], f, indent=2
                        )  # Save first 100 records
                    print(f"💾 Saved sample data to {sample_file}")

            else:
                print(f"❌ No data retrieved for {gold_epic}")

                # Try other resolutions
                print(f"\n🔄 Trying different resolutions...")
                for resolution in ["HOUR", "DAY", "WEEK"]:
                    print(f"\n📊 Testing {resolution} resolution...")
                    data = await tester.fetch_historical_data(
                        gold_epic, resolution=resolution, days_back=30
                    )
                    if data:
                        print(
                            f"✅ {resolution} resolution worked! Got {len(data)} records"
                        )
                        break

        else:
            print("❌ No gold markets found!")

    except Exception as e:
        print(f"❌ Test error: {e}")

    finally:
        await tester.cleanup()
        print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
