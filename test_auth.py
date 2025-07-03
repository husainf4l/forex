#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from capital_api import CapitalAPI

# Load environment variables
load_dotenv()

def main():
    print("🚀 Capital.com API Authentication Test")
    print("=" * 50)
    
    # Initialize Capital.com API (production environment)
    api = CapitalAPI(demo=False)
    
    # Test authentication
    if api.login():
        print("\n✅ Successfully authenticated with Capital.com!")
        
        # Test if authenticated
        if api.is_authenticated():
            print("✅ Authentication status confirmed")
            
            # Display account info
            print(f"📊 Account ID: {api.account_id}")
            print(f"👤 Client ID: {api.client_id}")
            print(f"🌐 Streaming Host: {api.streaming_host}")
            
            # Test market data
            print("\n🔍 Testing market data...")
            gold_price = api.get_gold_price()
            if gold_price:
                print("✅ Gold price data retrieved successfully")
                print(f"📊 Gold data preview: {str(gold_price)[:200]}...")
            else:
                print("❌ Failed to retrieve gold price data")
            
            # Test available markets
            print("\n🏪 Testing available markets...")
            markets = api.get_available_markets()
            if markets:
                print("✅ Markets data retrieved successfully")
                print(f"📊 Markets data preview: {str(markets)[:200]}...")
            else:
                print("❌ Failed to retrieve markets data")
                
            # Logout
            print("\n🔐 Logging out...")
            if api.logout():
                print("✅ Logout successful")
            else:
                print("❌ Logout failed")
        else:
            print("❌ Authentication status check failed")
    else:
        print("\n❌ Authentication failed")

if __name__ == "__main__":
    main()
