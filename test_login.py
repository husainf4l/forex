#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_capital_login():
    """Test Capital.com API login using curl-equivalent request"""
    
    # Get credentials from .env file
    api_key = os.getenv('CAPITAL_API_KEY')
    password = os.getenv('CAPITAL_CUSTOM_KEY')
    
    print(f"🔑 API Key: {api_key}")
    print(f"🔑 Password: {password}")
    
    # API endpoint
    url = "https://api-capital.backend-capital.com/api/v1/session"
    
    # Headers
    headers = {
        'X-CAP-API-KEY': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Request data
    data = {
        "identifier": api_key,
        "password": password,
        "encryptedPassword": False
    }
    
    print(f"\n🌐 Making request to: {url}")
    print(f"📋 Headers: {json.dumps(headers, indent=2)}")
    print(f"📦 Data: {json.dumps(data, indent=2)}")
    
    try:
        # Make the request with timeout
        response = requests.post(
            url, 
            headers=headers, 
            json=data, 
            timeout=30
        )
        
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        # Try to parse JSON response
        try:
            response_json = response.json()
            print(f"📦 Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"📦 Response Body (text): {response.text}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Capital.com API Login")
    print("=" * 50)
    
    success = test_capital_login()
    
    if success:
        print("\n✅ Login successful!")
    else:
        print("\n❌ Login failed!")
