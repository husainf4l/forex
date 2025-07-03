#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_capital_login():
    """Test Capital.com API login using the simplified approach"""
    
    # Get credentials from .env file
    API_KEY = os.getenv('CAPITAL_API_KEY')
    API_PASSWORD = os.getenv('CAPITAL_CUSTOM_KEY')
    EMAIL = "husain.f4l@gmail.com"
    
    print(f"🔑 API Key: {API_KEY}")
    print(f"🔑 API Password: {API_PASSWORD}")
    print(f"📧 Email: {EMAIL}")
    
    # API endpoint
    url = "https://api-capital.backend-capital.com/api/v1/session"
    
    # Headers
    headers = {
        "X-CAP-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Request payload
    payload = {
        "identifier": EMAIL,
        "password": API_PASSWORD
    }
    
    print(f"\n🌐 Making request to: {url}")
    print(f"📋 Headers: {json.dumps(headers, indent=2)}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"📦 Response Text: {response.text}")
        
        # Try to parse JSON response
        try:
            response_json = response.json()
            print(f"📦 Response JSON: {json.dumps(response_json, indent=2)}")
            
            # If successful, extract tokens
            if response.status_code == 200:
                cst = response.headers.get('CST')
                security_token = response.headers.get('X-SECURITY-TOKEN')
                print(f"🎫 CST Token: {cst}")
                print(f"🔐 Security Token: {security_token}")
                
        except:
            print("📦 Response is not valid JSON")
        
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
