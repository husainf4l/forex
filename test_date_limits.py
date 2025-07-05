#!/usr/bin/env python3
"""
Test Capital.com API date range limits
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# Capital.com API configuration
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
BASE_URL = "https://api-capital.backend-capital.com"


async def test_date_ranges():
    """Test different date ranges to find API limits"""

    # Login first
    timeout = aiohttp.ClientTimeout(total=30)
    session = aiohttp.ClientSession(timeout=timeout)

    headers = {"X-CAP-API-KEY": CAPITAL_API_KEY, "Content-Type": "application/json"}

    # Login
    login_data = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}
    async with session.post(
        f"{BASE_URL}/api/v1/session", json=login_data, headers=headers
    ) as response:
        if response.status == 200:
            cst_token = response.headers.get("CST")
            x_security_token = response.headers.get("X-SECURITY-TOKEN")
            headers.update({"CST": cst_token, "X-SECURITY-TOKEN": x_security_token})
            print("✅ Login successful")
        else:
            print("❌ Login failed")
            return

    # Test different date ranges
    now = datetime.now()
    base_date = now - timedelta(days=60)  # Start from 60 days ago

    # Test ranges from 1 hour to 30 days
    test_ranges = [
        {"hours": 1, "name": "1 hour"},
        {"hours": 6, "name": "6 hours"},
        {"hours": 12, "name": "12 hours"},
        {"hours": 24, "name": "1 day"},
        {"hours": 48, "name": "2 days"},
        {"hours": 72, "name": "3 days"},
        {"hours": 168, "name": "1 week"},
        {"hours": 336, "name": "2 weeks"},
        {"hours": 720, "name": "30 days"},
    ]

    resolutions = ["MINUTE", "MINUTE_5", "HOUR"]

    for resolution in resolutions:
        print(f"\n📊 Testing {resolution} resolution:")
        print("=" * 50)

        for test_range in test_ranges:
            to_date = base_date
            from_date = to_date - timedelta(hours=test_range["hours"])

            from_str = from_date.strftime("%Y-%m-%dT%H:%M:%S")
            to_str = to_date.strftime("%Y-%m-%dT%H:%M:%S")

            url = f"{BASE_URL}/api/v1/prices/GOLD"
            params = {
                "resolution": resolution,
                "from": from_str,
                "to": to_str,
                "max": 100,
            }

            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])
                        print(f"✅ {test_range['name']}: {len(prices)} records")
                        if len(prices) > 0:
                            # Show the structure of the first record
                            print(f"   📊 Sample record: {prices[0]}")
                            print(f"   📅 Date range: {from_str} to {to_str}")
                            break
                    else:
                        error_text = await response.text()
                        print(
                            f"❌ {test_range['name']}: {response.status} - {error_text}"
                        )
            except Exception as e:
                print(f"❌ {test_range['name']}: {e}")

    await session.close()


if __name__ == "__main__":
    asyncio.run(test_date_ranges())
