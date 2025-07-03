# Capital.com API Integration
import requests
import json
from typing import Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class CapitalAPI:
    def __init__(self, demo=False):
        # Load credentials from .env file
        self.api_key = os.getenv('CAPITAL_API_KEY')
        self.email = os.getenv('CAPITAL_EMAIL')
        self.password = os.getenv('CAPITAL_PASSWORD')
        
        # Debug credential loading
        print(f"🔑 API Key loaded: {'✅' if self.api_key else '❌'}")
        print(f"📧 Email loaded: {'✅' if self.email else '❌'}")
        print(f"🔑 Password loaded: {'✅' if self.password else '❌'}")
        
        # API URLs
        self.base_url = "https://demo-api-capital.backend-capital.com" if demo else "https://api-capital.backend-capital.com"
        
        # Authentication tokens
        self.session_token = None
        self.security_token = None
        
        # Account info
        self.account_id = None
        self.client_id = None
        self.streaming_host = None
        
        # Base headers
        self.headers = {
            'X-CAP-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Version': '1'
        }
    
    def login(self) -> bool:
        """Login to Capital.com API using email and API password"""
        print("🔄 Attempting Capital.com API authentication...")
        
        # Validate credentials
        if not all([self.api_key, self.email, self.password]):
            print("❌ Missing credentials. Please check your .env file.")
            return False
        
        # API endpoint
        url = f"{self.base_url}/api/v1/session"
        
        # Headers
        headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Request payload
        payload = {
            "identifier": self.email,
            "password": self.password
        }
        
        print(f"🌐 Making request to: {url}")
        print(f"📧 Using email: {self.email}")
        print(f"🔑 Using API key: {self.api_key[:10]}...")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            print(f"✅ Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract tokens from headers
                self.session_token = response.headers.get('CST')
                self.security_token = response.headers.get('X-SECURITY-TOKEN')
                
                print(f"🎫 CST Token: {self.session_token}")
                print(f"🔐 Security Token: {self.security_token}")
                
                # Update headers for future requests
                self.headers.update({
                    'CST': self.session_token,
                    'X-SECURITY-TOKEN': self.security_token
                })
                
                # Store account info
                response_data = response.json()
                self.account_id = response_data.get('currentAccountId')
                self.client_id = response_data.get('clientId')
                self.streaming_host = response_data.get('streamingHost')
                
                print(f"📊 Account ID: {self.account_id}")
                print(f"👤 Client ID: {self.client_id}")
                print(f"🌐 Streaming Host: {self.streaming_host}")
                
                return True
            else:
                print(f"❌ Login failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📦 Error response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📦 Error response (text): {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False
    def is_authenticated(self) -> bool:
        """Check if the API is authenticated"""
        return self.session_token is not None and self.security_token is not None
    
    def logout(self) -> bool:
        """Logout from Capital.com API"""
        if not self.is_authenticated():
            print("❌ Not authenticated, cannot logout")
            return False
        
        url = f"{self.base_url}/api/v1/session"
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code == 204:
                print("✅ Logout successful")
                self.session_token = None
                self.security_token = None
                self.headers = {
                    'X-CAP-API-KEY': self.api_key,
                    'Content-Type': 'application/json',
                    'Version': '1'
                }
                return True
            else:
                print(f"❌ Logout failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Logout request failed: {e}")
            return False

    def get_gold_price(self) -> Optional[Dict]:
        """Get live GOLD price"""
        if not self.session_token:
            if not self.login():
                return None
        
        url = f"{self.base_url}/api/v1/prices/GOLD"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": "GOLD",
                    "bid": float(data.get('bid', 0)),
                    "offer": float(data.get('offer', 0)),
                    "high": float(data.get('high', 0)),
                    "low": float(data.get('low', 0)),
                    "price_change": float(data.get('netChange', 0)),
                    "price_change_percent": float(data.get('pctChange', 0)),
                    "timestamp": datetime.now().isoformat(),
                    "market_status": data.get('marketStatus', 'UNKNOWN')
                }
            else:
                print(f"Failed to get gold price: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting gold price: {e}")
            return None
    
    def get_market_info(self) -> Optional[Dict]:
        """Get GOLD market information"""
        if not self.session_token:
            if not self.login():
                return None
        
        url = f"{self.base_url}/api/v1/markets/GOLD"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting market info: {e}")
            return None
    
    def test_connection(self) -> Dict:
        """Test the Capital.com API connection and endpoints"""
        results = {
            "api_key_present": bool(self.api_key),
            "custom_key_present": bool(self.custom_key),
            "base_url": self.base_url,
            "login_test": False,
            "endpoints_test": {}
        }
        
        # Test login
        print("🧪 Testing Capital.com API connection...")
        results["login_test"] = self.login()
        
        if results["login_test"]:
            # Test endpoints if login successful
            endpoints = [
                ("/api/v1/markets", "markets"),
                ("/api/v1/prices", "prices"), 
                ("/api/v1/markets/GOLD", "gold_market"),
                ("/api/v1/prices/GOLD", "gold_price")
            ]
            
            for endpoint, name in endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.get(url, headers=self.headers, timeout=10)
                    results["endpoints_test"][name] = {
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "response_size": len(response.text) if response.text else 0
                    }
                    print(f"✅ {name}: {response.status_code}")
                except Exception as e:
                    results["endpoints_test"][name] = {
                        "status_code": 0,
                        "success": False,
                        "error": str(e)
                    }
                    print(f"❌ {name}: {str(e)}")
        
        return results
    
    def get_available_markets(self) -> Optional[Dict]:
        """Get list of available markets from Capital.com"""
        if not self.session_token:
            if not self.login():
                return None
        
        url = f"{self.base_url}/api/v1/markets"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get markets: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting markets: {e}")
            return None
